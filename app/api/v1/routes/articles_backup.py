"""
API routes for scientific article processing
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import List
from datetime import datetime
from pathlib import Path
import time
import json

from app.db.mongodb import get_mongo_db
from app.services.article_processor import article_processor
from app.services.tag_generator import tag_generator
from app.services.embeddings import embedding_service
from app.services.duplicate_detection import duplicate_detector
from app.schemas.articles import (
    ArticleInput,
    ArticleProcessResponse,
    BatchArticleProcessResponse
)


router = APIRouter(prefix="/articles", tags=["Article Processing"])


@router.post("/process", response_model=BatchArticleProcessResponse)
async def process_articles(
    articles: List[ArticleInput] = Body(..., description="List of articles to process"),
    generate_embeddings: bool = Query(True, description="Generate embeddings for chunks"),
    generate_tags: bool = Query(True, description="Generate tags automatically"),
    max_tags: int = Query(15, ge=1, le=30, description="Maximum number of tags"),
    chunk_size: int = Query(1000, ge=100, le=5000, description="Chunk size in characters"),
    chunk_overlap: int = Query(200, ge=0, le=1000, description="Overlap between chunks"),
    dry_run: bool = Query(False, description="If true, save chunks to txt file instead of DB"),
    check_duplicates: bool = Query(True, description="Check for duplicate chunks before inserting"),
    similarity_threshold: float = Query(0.95, ge=0.0, le=1.0, description="Similarity threshold for duplicate detection (0-1)"),
    db = Depends(get_mongo_db)
):
    """
    Process multiple scientific articles into chunks with embeddings
    
    - Extracts text from articles (title, abstract, full_text)
    - Splits into chunks
    - Checks for duplicate chunks using vector similarity
    - Generates embeddings for each chunk
    - Generates tags automatically
    - Stores unique chunks in MongoDB (or txt files if dry_run=true)
    
    Returns processing summary for each article
    """
    
    start_time = time.time()
    
    # Update duplicate detector threshold
    duplicate_detector.similarity_threshold = similarity_threshold
    
    results = []
    total_chunks_created = 0
    failed_articles = []
    
    print(f"\n{'='*70}")
    print(f"� BATCH PROCESSING: {len(articles)} articles")
    print(f"{'='*70}\n")
    
    try:
        # Configure article processor
        article_processor.chunk_size = chunk_size
        article_processor.chunk_overlap = chunk_overlap
        
        # Process article
        result = article_processor.process_article(article.dict())
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "Processing failed"))
        
        print(f"✅ Extracted {result['total_chars']} chars, {result['total_words']} words")
        print(f"✅ Created {len(result['chunks'])} chunks")
        
        # Generate tags from full text
        tags = []
        category = "scientific"
        
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
        
        # Process chunks
        chunk_ids = []
        chunks_with_embeddings = 0
        
        # DRY RUN: Save to txt file
        if dry_run:
            dry_run_dir = Path("dry_runs/articles")
            dry_run_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            safe_title = "".join(c for c in article.title[:50] if c.isalnum() or c in (' ', '-', '_')).strip()
            filename = dry_run_dir / f"{safe_title}-{timestamp}.txt"
            
            with open(filename, "w", encoding="utf-8") as f:
                f.write(f"{'='*70}\n")
                f.write(f"ARTICLE DRY RUN - {datetime.now().isoformat()}\n")
                f.write(f"{'='*70}\n\n")
                f.write(f"Title: {article.title}\n")
                f.write(f"Authors: {', '.join(article.authors)}\n")
                f.write(f"URL: {article.url}\n")
                f.write(f"Tags: {', '.join(tags)}\n")
                f.write(f"Category: {category}\n")
                f.write(f"\n{'='*70}\n")
                f.write(f"METADATA\n")
                f.write(f"{'='*70}\n")
                f.write(json.dumps(result["metadata"], indent=2, ensure_ascii=False))
                f.write(f"\n\n{'='*70}\n")
                f.write(f"CHUNKS ({len(result['chunks'])} total)\n")
                f.write(f"{'='*70}\n\n")
                
                for i, chunk_data in enumerate(result["chunks"], 1):
                    f.write(f"\n--- CHUNK {i}/{len(result['chunks'])} ---\n")
                    f.write(f"Characters: {chunk_data['char_count']}\n")
                    f.write(f"Words: {chunk_data['word_count']}\n")
                    f.write(f"Sentences: {len(chunk_data['sentences'])}\n")
                    
                    if generate_embeddings:
                        embedding = embedding_service.generate_embedding(chunk_data["text"])
                        if embedding:
                            f.write(f"Embedding: {len(embedding)} dimensions\n")
                            f.write(f"Embedding preview: [{', '.join(map(str, embedding[:5]))}...]\n")
                            chunks_with_embeddings += 1
                    
                    f.write(f"\nText:\n{chunk_data['text']}\n")
                    f.write(f"\n{'-'*70}\n")
            
            print(f"\n💾 DRY RUN: Saved to {filename}")
            
            processing_time = time.time() - start_time
            
            return ArticleProcessResponse(
                success=True,
                article_title=article.title,
                summary={
                    "total_chars": result["total_chars"],
                    "total_words": result["total_words"],
                    "total_chunks": len(result["chunks"]),
                    "chunks_with_embeddings": chunks_with_embeddings,
                    "tags": tags,
                    "category": category,
                    "processing_time_seconds": round(processing_time, 2),
                    "dry_run": True,
                    "dry_run_file": str(filename)
                },
                chunk_ids=[],
                metadata=result["metadata"]
            )
        
        # NORMAL RUN: Store in MongoDB
        print(f"\n💾 Storing chunks in MongoDB...")
        
        for chunk_data in result["chunks"]:
            # Prepare chunk document
            chunk_doc = {
                "pk": article.title,
                "text": chunk_data["text"],
                "source_type": "article",
                "source_url": article.url,
                "metadata": {
                    "article_metadata": result["metadata"],
                    "references": article.references,
                    "char_count": chunk_data["char_count"],
                    "word_count": chunk_data["word_count"],
                    "sentences_count": len(chunk_data["sentences"]),
                    "tags": tags,
                    "category": category
                },
                "chunk_index": chunk_data["chunk_index"],
                "total_chunks": chunk_data["total_chunks"],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            # Generate embedding if requested (for counting purposes only, not stored)
            if generate_embeddings:
                embedding = embedding_service.generate_embedding(chunk_data["text"])
                if embedding:
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
        
        return ArticleProcessResponse(
            success=True,
            article_title=article.title,
            summary={
                "total_chars": result["total_chars"],
                "total_words": result["total_words"],
                "total_chunks": len(chunk_ids),
                "chunks_with_embeddings": chunks_with_embeddings,
                "tags": tags,
                "category": category,
                "processing_time_seconds": round(processing_time, 2),
                "dry_run": False
            },
            chunk_ids=chunk_ids,
            metadata=result["metadata"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"\n❌ Error processing article: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing article: {str(e)}")


@router.post("/process-batch", response_model=BatchArticleProcessResponse)
async def process_article_batch(
    articles: List[ArticleInput],
    generate_embeddings: bool = Query(True, description="Generate embeddings for chunks"),
    generate_tags: bool = Query(True, description="Generate tags automatically"),
    dry_run: bool = Query(False, description="If true, save chunks to txt files instead of DB"),
    db = Depends(get_mongo_db)
):
    """
    Process multiple scientific articles in batch
    
    Returns summary for each processed article
    """
    
    results = []
    total_chunks = 0
    failed_articles = []
    
    print(f"\n{'='*70}")
    print(f"📦 BATCH PROCESSING: {len(articles)} articles")
    print(f"{'='*70}\n")
    
    for article in articles:
        try:
            # Process article
            result = article_processor.process_article(article.dict())
            
            if not result["success"]:
                failed_articles.append({
                    "title": article.title,
                    "error": result.get("error", "Processing failed")
                })
                continue
            
            # Generate tags
            tags = []
            category = "scientific"
            if generate_tags:
                tags = tag_generator.generate_tags(result["full_text"], max_tags=15)
                category = tag_generator.generate_category(result["full_text"], tags)
            
            # Store chunks or save to file
            chunk_ids = []
            
            if not dry_run:
                for chunk_data in result["chunks"]:
                    chunk_doc = {
                        "pk": article.title,
                        "text": chunk_data["text"],
                        "source_type": "article",
                        "source_url": article.url,
                        "metadata": {
                            "article_metadata": result["metadata"],
                            "char_count": chunk_data["char_count"],
                            "word_count": chunk_data["word_count"],
                            "tags": tags,
                            "category": category
                        },
                        "chunk_index": chunk_data["chunk_index"],
                        "total_chunks": chunk_data["total_chunks"],
                        "created_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                    
                    # Generate embedding if requested (for counting purposes only, not stored)
                    if generate_embeddings:
                        embedding = embedding_service.generate_embedding(chunk_data["text"])
                    
                    insert_result = await db['chunks'].insert_one(chunk_doc)
                    chunk_ids.append(str(insert_result.inserted_id))
            
            total_chunks += len(result["chunks"])
            
            results.append({
                "title": article.title,
                "success": True,
                "chunks_created": len(chunk_ids) if not dry_run else len(result["chunks"]),
                "tags": tags,
                "category": category
            })
            
        except Exception as e:
            failed_articles.append({
                "title": article.title,
                "error": str(e)
            })
    
    return BatchArticleProcessResponse(
        success=True,
        total_articles=len(articles),
        successful=len(results),
        failed=len(failed_articles),
        total_chunks_created=total_chunks,
        results=results,
        failed_articles=failed_articles
    )


@router.get("/stats")
async def get_article_stats(db = Depends(get_mongo_db)):
    """
    Get statistics about processed articles
    
    Returns:
        Statistics about article chunks in the database
    """
    
    # Count total article chunks
    total_article_chunks = await db['chunks'].count_documents({"source_type": "article"})
    
    # Get unique articles
    article_titles = await db['chunks'].distinct("pk", {"source_type": "article"})
    
    # Get chunks with embeddings
    chunks_with_embeddings = await db['chunks'].count_documents({
        "source_type": "article",
        "embedding": {"$ne": None}
    })
    
    # Get category distribution
    pipeline = [
        {"$match": {"source_type": "article"}},
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
        "total_article_chunks": total_article_chunks,
        "unique_articles": len(article_titles),
        "article_titles": article_titles,
        "chunks_with_embeddings": chunks_with_embeddings,
        "chunks_without_embeddings": total_article_chunks - chunks_with_embeddings,
        "category_distribution": category_distribution
    }
