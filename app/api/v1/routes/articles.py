"""
API routes for scientific article processing - COMPLETE REWRITE
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
from app.core.config import settings
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
    chunk_size: int = Query(1500, ge=100, le=5000, description="Chunk size in characters (default: 1500)"),
    chunk_overlap: int = Query(400, ge=0, le=1500, description="Overlap between chunks (~26%, default: 400)"),
    dry_run: bool = Query(default=None, description="If true, save chunks to txt files instead of DB. If None, uses DRY_RUN environment variable"),
    check_duplicates: bool = Query(True, description="Check for duplicate chunks before inserting"),
    similarity_threshold: float = Query(0.95, ge=0.0, le=1.0, description="Similarity threshold for duplicate detection"),
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
    
    # Use environment DRY_RUN if not explicitly provided
    if dry_run is None:
        dry_run = settings.DRY_RUN
    
    # Update duplicate detector threshold
    duplicate_detector.similarity_threshold = similarity_threshold
    
    results = []
    total_chunks_created = 0
    failed_articles = []
    
    print(f"\n{'='*70}")
    print(f"📦 BATCH PROCESSING: {len(articles)} articles")
    if dry_run:
        print(f"⚠️  DRY_RUN MODE: Saving to TXT files in dry_runs/articles/")
    print(f"{'='*70}\n")
    
    # Configure article processor
    article_processor.chunk_size = chunk_size
    article_processor.chunk_overlap = chunk_overlap
    
    for article in articles:
        try:
            print(f"\n📄 Processing: {article.title[:60]}...")
            
            # Process article
            result = article_processor.process_article(article.dict())
            
            if not result["success"]:
                failed_articles.append({
                    "title": article.title,
                    "error": result.get("error", "Processing failed")
                })
                continue
            
            print(f"   ✅ Extracted {result['total_chars']} chars, {len(result['chunks'])} chunks")
            
            # Generate tags from full text
            tags = []
            category = "scientific"
            
            if generate_tags:
                tags = tag_generator.generate_tags(
                    text=result["full_text"],
                    max_tags=max_tags,
                    include_domain=True,
                    include_entities=True
                )
                category = tag_generator.generate_category(result["full_text"], tags)
                print(f"   🏷️  Tags: {', '.join(tags[:5])}...")
            
            chunk_ids = []
            chunks_with_embeddings = 0
            duplicates_found = 0
            duplicates_skipped = 0
            
            # DRY RUN: Save to txt file
            if dry_run:
                dry_run_dir = Path("dry_runs/articles")
                dry_run_dir.mkdir(parents=True, exist_ok=True)
                
                timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                # Normalize title: lowercase, no spaces, only alphanumeric and hyphens
                normalized_title = "".join(c if c.isalnum() else '-' for c in article.title[:50].lower()).strip('-')
                # Remove consecutive hyphens
                while '--' in normalized_title:
                    normalized_title = normalized_title.replace('--', '-')
                filename = dry_run_dir / f"{normalized_title}-{timestamp}.txt"
                
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
                            # Generate embedding with tags included
                            text_with_metadata = chunk_data["text"]
                            if tags:
                                text_with_metadata += f"\n\nKeywords: {', '.join(tags)}"
                            if category:
                                text_with_metadata += f"\nCategory: {category}"
                            
                            embedding = embedding_service.generate_embedding(text_with_metadata)
                            if embedding:
                                f.write(f"Embedding: {len(embedding)} dimensions\n")
                                f.write(f"Embedding preview: [{', '.join(map(str, embedding[:5]))}...]\n")
                                chunks_with_embeddings += 1
                        
                        f.write(f"\nText:\n{chunk_data['text']}\n")
                        f.write(f"\n{'-'*70}\n")
                
                print(f"   💾 DRY RUN: Saved to {filename}")
                
                results.append({
                    "title": article.title,
                    "success": True,
                    "chunks_created": len(result["chunks"]),
                    "duplicates_skipped": 0,
                    "tags": tags,
                    "category": category,
                    "dry_run_file": str(filename)
                })
                
                total_chunks_created += len(result["chunks"])
                continue
            
            # NORMAL RUN: Store in MongoDB with duplicate detection
            print(f"   💾 Storing chunks in MongoDB...")
            
            for chunk_data in result["chunks"]:
                # Check for duplicates if enabled
                is_duplicate = False
                
                if check_duplicates:
                    duplicate = await duplicate_detector.find_similar_chunk(
                        text=chunk_data["text"],
                        db=db,
                        source_type="article"
                    )
                    
                    if duplicate:
                        is_duplicate = True
                        duplicates_found += 1
                        duplicates_skipped += 1
                        print(f"      ⚠️  Duplicate found (similarity: {duplicate['similarity']:.2%}), skipping...")
                
                if not is_duplicate:
                    # Normalize title for pk: lowercase, no spaces, only alphanumeric and hyphens
                    normalized_pk = "".join(c if c.isalnum() else '-' for c in article.title.lower()).strip('-')
                    # Remove consecutive hyphens
                    while '--' in normalized_pk:
                        normalized_pk = normalized_pk.replace('--', '-')
                    
                    # Prepare chunk document
                    chunk_doc = {
                        "pk": normalized_pk,
                        "text": chunk_data["text"],
                        "abstract": article.abstract if article.abstract else "",
                        "publication_year": article.publication_year if hasattr(article, 'publication_year') else None,
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
                    
                    # Generate embedding if requested and add to document
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
                            chunks_with_embeddings += 1
                    
                    # Insert into MongoDB
                    insert_result = await db['chunks'].insert_one(chunk_doc)
                    chunk_ids.append(str(insert_result.inserted_id))
            
            total_chunks_created += len(chunk_ids)
            
            print(f"   ✅ Stored {len(chunk_ids)} chunks ({duplicates_skipped} duplicates skipped)")
            
            results.append({
                "title": article.title,
                "success": True,
                "chunks_created": len(chunk_ids),
                "duplicates_skipped": duplicates_skipped,
                "tags": tags,
                "category": category
            })
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            failed_articles.append({
                "title": article.title,
                "error": str(e)
            })
    
    processing_time = time.time() - start_time
    
    print(f"\n{'='*70}")
    print(f"✅ BATCH PROCESSING COMPLETE!")
    print(f"{'='*70}")
    print(f"  📊 Total articles: {len(articles)}")
    print(f"  ✅ Successful: {len(results)}")
    print(f"  ❌ Failed: {len(failed_articles)}")
    print(f"  📦 Total chunks created: {total_chunks_created}")
    print(f"  ⏱️  Processing time: {processing_time:.2f}s")
    print(f"{'='*70}\n")
    
    return BatchArticleProcessResponse(
        success=True,
        total_articles=len(articles),
        successful=len(results),
        failed=len(failed_articles),
        total_chunks_created=total_chunks_created,
        results=results,
        failed_articles=failed_articles
    )


@router.post("/process-batch", response_model=BatchArticleProcessResponse)
async def process_article_batch(
    articles: List[ArticleInput],
    generate_embeddings: bool = Query(True, description="Generate embeddings for chunks"),
    generate_tags: bool = Query(True, description="Generate tags automatically"),
    dry_run: bool = Query(False, description="If true, save chunks to txt files instead of DB"),
    check_duplicates: bool = Query(True, description="Check for duplicate chunks before inserting"),
    db = Depends(get_mongo_db)
):
    """
    DEPRECATED: Use /process endpoint instead (it now accepts arrays)
    
    This endpoint is kept for backward compatibility
    """
    return await process_articles(
        articles=articles,
        generate_embeddings=generate_embeddings,
        generate_tags=generate_tags,
        dry_run=dry_run,
        check_duplicates=check_duplicates,
        db=db
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
        "article_titles": article_titles[:100],  # Limit to first 100
        "category_distribution": category_distribution
    }
