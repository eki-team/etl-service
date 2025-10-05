"""
API routes for PDF document processing
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from typing import List, Optional
from datetime import datetime
import time

from app.db.mongodb import get_mongo_db
from app.services.pdf_processor import pdf_processor
from app.services.tag_generator import tag_generator
from app.services.embeddings import embedding_service
from app.schemas.vectors import ChunkResponse


router = APIRouter(prefix="/pdf", tags=["PDF Processing"])


@router.post("/upload")
async def upload_pdf(
    file: UploadFile = File(..., description="PDF file to process"),
    generate_embeddings: bool = Query(True, description="Generate embeddings for chunks"),
    generate_tags: bool = Query(True, description="Generate tags automatically"),
    max_tags: int = Query(15, ge=1, le=30, description="Maximum number of tags"),
    chunk_size: int = Query(1000, ge=100, le=5000, description="Chunk size in characters"),
    chunk_overlap: int = Query(200, ge=0, le=1000, description="Overlap between chunks"),
    extraction_method: str = Query("pdfplumber", description="Text extraction method"),
    db = Depends(get_mongo_db)
):
    """
    Upload and process a PDF document
    
    - Extracts text from PDF
    - Splits into chunks
    - Generates embeddings for each chunk
    - Generates tags automatically
    - Stores chunks in MongoDB
    
    Returns processing summary and chunk IDs
    """
    
    start_time = time.time()
    
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    print(f"\n{'='*70}")
    print(f"📄 PROCESSING PDF: {file.filename}")
    print(f"{'='*70}")
    
    try:
        # Read PDF content
        pdf_content = await file.read()
        print(f"✅ Read {len(pdf_content)} bytes")
        
        # Configure PDF processor with custom settings
        pdf_processor.chunk_size = chunk_size
        pdf_processor.chunk_overlap = chunk_overlap
        
        # Process PDF
        result = pdf_processor.process_pdf(
            pdf_bytes=pdf_content,
            filename=file.filename,
            extraction_method=extraction_method
        )
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "Processing failed"))
        
        # Generate tags from full text
        tags = []
        category = "general"
        
        if generate_tags:
            print(f"\n🏷️  Generating tags...")
            tags = tag_generator.generate_tags(
                text=result["full_text"],
                max_tags=max_tags,
                include_domain=True,
                include_entities=True
            )
            category = tag_generator.generate_category(result["full_text"], tags)
            print(f"  ✅ Generated {len(tags)} tags: {', '.join(tags[:10])}")
            print(f"  📁 Category: {category}")
        
        # Process chunks and store in MongoDB
        print(f"\n💾 Storing chunks in MongoDB...")
        chunk_ids = []
        chunks_with_embeddings = 0
        
        for chunk_data in result["chunks"]:
            # Prepare chunk document
            chunk_doc = {
                "pk": file.filename,
                "text": chunk_data["text"],
                "abstract": "",  # PDFs don't have separate abstract field
                "source_type": "pdf",
                "metadata": {
                    "pdf_metadata": result["metadata"],
                    "char_count": chunk_data["char_count"],
                    "word_count": chunk_data["word_count"],
                    "sentences_count": len(chunk_data["sentences"]),
                    "tags": tags,
                    "category": category,
                    "extraction_method": extraction_method
                },
                "chunk_index": chunk_data["chunk_index"],
                "total_chunks": chunk_data["total_chunks"],
                "embedding": None,
                "embedding_model": None,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            # Generate embedding if requested (include tags for better search)
            if generate_embeddings:
                # Include tags and category in the embedding
                text_with_metadata = chunk_data["text"]
                if tags:
                    text_with_metadata += f"\n\nKeywords: {', '.join(tags)}"
                if category:
                    text_with_metadata += f"\nCategory: {category}"
                
                embedding = embedding_service.generate_embedding(text_with_metadata)
                if embedding:
                    chunk_doc["embedding"] = embedding
                    chunk_doc["embedding_model"] = embedding_service.model_name
                    chunks_with_embeddings += 1
            
            # Insert into MongoDB
            insert_result = await db['chunks'].insert_one(chunk_doc)
            chunk_ids.append(str(insert_result.inserted_id))
        
        processing_time = time.time() - start_time
        
        print(f"\n{'='*70}")
        print(f"✅ PROCESSING COMPLETE!")
        print(f"{'='*70}")
        print(f"  📊 Total chunks: {len(chunk_ids)}")
        print(f"  🧠 Chunks with embeddings: {chunks_with_embeddings}")
        print(f"  🏷️  Tags: {len(tags)}")
        print(f"  ⏱️  Processing time: {processing_time:.2f}s")
        print(f"{'='*70}\n")
        
        # Return summary
        return {
            "success": True,
            "message": f"Successfully processed {file.filename}",
            "filename": file.filename,
            "summary": {
                "total_chars": result["total_chars"],
                "total_words": result["total_words"],
                "total_chunks": len(chunk_ids),
                "chunks_with_embeddings": chunks_with_embeddings,
                "num_pages": result["metadata"]["num_pages"],
                "tags": tags,
                "category": category,
                "processing_time_seconds": round(processing_time, 2)
            },
            "chunk_ids": chunk_ids,
            "pdf_metadata": result["metadata"]["info"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"\n❌ Error processing PDF: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")


@router.post("/upload-batch")
async def upload_pdf_batch(
    files: List[UploadFile] = File(..., description="Multiple PDF files to process"),
    generate_embeddings: bool = Query(True, description="Generate embeddings for chunks"),
    generate_tags: bool = Query(True, description="Generate tags automatically"),
    db = Depends(get_mongo_db)
):
    """
    Upload and process multiple PDF documents in batch
    
    Returns summary for each processed file
    """
    
    results = []
    total_chunks = 0
    failed_files = []
    
    print(f"\n{'='*70}")
    print(f"📦 BATCH PROCESSING: {len(files)} files")
    print(f"{'='*70}\n")
    
    for file in files:
        try:
            # Process each file using the single upload endpoint logic
            pdf_content = await file.read()
            
            result = pdf_processor.process_pdf(
                pdf_bytes=pdf_content,
                filename=file.filename,
                extraction_method="pdfplumber"
            )
            
            if not result["success"]:
                failed_files.append({
                    "filename": file.filename,
                    "error": result.get("error", "Processing failed")
                })
                continue
            
            # Generate tags
            tags = []
            category = "general"
            if generate_tags:
                tags = tag_generator.generate_tags(result["full_text"], max_tags=15)
                category = tag_generator.generate_category(result["full_text"], tags)
            
            # Store chunks
            chunk_ids = []
            for chunk_data in result["chunks"]:
                chunk_doc = {
                    "text": chunk_data["text"],
                    "abstract": "",  # PDFs don't have separate abstract field
                    "source": file.filename,
                    "source_type": "pdf",
                    "metadata": {
                        "pdf_metadata": result["metadata"],
                        "char_count": chunk_data["char_count"],
                        "word_count": chunk_data["word_count"],
                        "tags": tags,
                        "category": category
                    },
                    "chunk_index": chunk_data["chunk_index"],
                    "total_chunks": chunk_data["total_chunks"],
                    "embedding": None,
                    "embedding_model": None,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
                
                if generate_embeddings:
                    embedding = embedding_service.generate_embedding(chunk_data["text"])
                    if embedding:
                        chunk_doc["embedding"] = embedding
                        chunk_doc["embedding_model"] = embedding_service.model_name
                
                insert_result = await db['chunks'].insert_one(chunk_doc)
                chunk_ids.append(str(insert_result.inserted_id))
            
            total_chunks += len(chunk_ids)
            
            results.append({
                "filename": file.filename,
                "success": True,
                "chunks_created": len(chunk_ids),
                "tags": tags,
                "category": category
            })
            
        except Exception as e:
            failed_files.append({
                "filename": file.filename,
                "error": str(e)
            })
    
    return {
        "success": True,
        "total_files": len(files),
        "successful": len(results),
        "failed": len(failed_files),
        "total_chunks_created": total_chunks,
        "results": results,
        "failed_files": failed_files
    }


@router.get("/chunks/{source_filename}", response_model=List[ChunkResponse])
async def get_chunks_by_pdf(
    source_filename: str,
    db = Depends(get_mongo_db)
):
    """
    Get all chunks from a specific PDF file
    
    Args:
        source_filename: Name of the PDF file
        
    Returns:
        List of chunks from that PDF
    """
    
    cursor = db['chunks'].find(
        {"source": source_filename, "source_type": "pdf"}
    ).sort("chunk_index", 1)
    
    chunks = []
    async for chunk in cursor:
        chunk["id"] = str(chunk.pop("_id"))
        chunk.pop("embedding", None)  # Remove embedding for performance
        chunks.append(ChunkResponse(**chunk))
    
    if not chunks:
        raise HTTPException(status_code=404, detail=f"No chunks found for PDF: {source_filename}")
    
    return chunks


@router.get("/stats")
async def get_pdf_stats(db = Depends(get_mongo_db)):
    """
    Get statistics about processed PDFs
    
    Returns:
        Statistics about PDF chunks in the database
    """
    
    # Count total PDF chunks
    total_pdf_chunks = await db['chunks'].count_documents({"source_type": "pdf"})
    
    # Get unique PDF files
    pdf_sources = await db['chunks'].distinct("source", {"source_type": "pdf"})
    
    # Get chunks with embeddings
    chunks_with_embeddings = await db['chunks'].count_documents({
        "source_type": "pdf",
        "embedding": {"$ne": None}
    })
    
    # Get category distribution
    pipeline = [
        {"$match": {"source_type": "pdf"}},
        {"$group": {
            "_id": "$metadata.category",
            "count": {"$sum": 1}
        }},
        {"$sort": {"count": -1}}
    ]
    
    category_distribution = []
    async for doc in db['chunks'].aggregate(pipeline):
        category_distribution.append({
            "category": doc["_id"],
            "count": doc["count"]
        })
    
    return {
        "total_pdf_chunks": total_pdf_chunks,
        "unique_pdfs": len(pdf_sources),
        "pdf_files": pdf_sources,
        "chunks_with_embeddings": chunks_with_embeddings,
        "chunks_without_embeddings": total_pdf_chunks - chunks_with_embeddings,
        "category_distribution": category_distribution
    }
