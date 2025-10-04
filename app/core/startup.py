"""
Startup script for ETL service
Initializes MongoDB and loads articles from JSON files
"""
import json
import asyncio
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

from app.db.mongodb import get_mongo_db
from app.services.article_processor import ArticleProcessor
from app.services.tag_generator import tag_generator
from app.services.embeddings import embedding_service
from app.services.duplicate_detection import duplicate_detector
from app.schemas.articles import ArticleInput
from app.core.config import settings


async def ensure_collections():
    """Ensure required MongoDB collections exist with proper indexes"""
    # Skip MongoDB initialization in DRY_RUN mode
    if settings.DRY_RUN:
        print("🔧 Skipping MongoDB collections initialization (DRY_RUN mode)")
        return
    
    print("🔧 Initializing MongoDB collections...")
    
    db = await get_mongo_db()
    
    if db is None:
        print("   ⚠️  No database connection available")
        return
    
    # Create chunks collection if it doesn't exist
    collections = await db.list_collection_names()
    
    if "chunks" not in collections:
        await db.create_collection("chunks")
        print("   ✅ Created 'chunks' collection")
    else:
        print("   ℹ️  Collection 'chunks' already exists")
    
    # Create indexes for better performance
    await db.chunks.create_index("pk")
    await db.chunks.create_index("source_type")
    await db.chunks.create_index("created_at")
    await db.chunks.create_index([("metadata.tags", 1)])
    print("   ✅ Indexes created/verified")


async def load_articles_from_json(
    json_path: Path,
    check_duplicates: bool = False,  # Disabled by default for faster loading
    similarity_threshold: float = 0.95
) -> Dict[str, Any]:
    """
    Load and process articles from a JSON file
    
    Args:
        json_path: Path to JSON file with articles
        check_duplicates: Whether to check for duplicate chunks
        similarity_threshold: Threshold for duplicate detection
        
    Returns:
        Processing statistics
    """
    print(f"\n📄 Loading articles from: {json_path.name}")
    
    if not json_path.exists():
        print(f"   ⚠️  File not found: {json_path}")
        return {"success": False, "error": "File not found"}
    
    # Load JSON
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            articles_data = json.load(f)
        print(f"   ✅ Loaded {len(articles_data)} articles from JSON")
    except Exception as e:
        print(f"   ❌ Error loading JSON: {e}")
        return {"success": False, "error": str(e)}
    
    # Process articles
    db = await get_mongo_db() if not settings.DRY_RUN else None
    article_processor = ArticleProcessor(chunk_size=1500, chunk_overlap=400)
    
    total_articles = len(articles_data)
    total_chunks_created = 0
    total_duplicates_skipped = 0
    articles_processed = 0
    articles_failed = 0
    
    for idx, article_data in enumerate(articles_data, 1):
        try:
            print(f"\n   📰 Processing article {idx}/{total_articles}: {article_data.get('title', 'Untitled')[:60]}...")
            
            # Process article into chunks
            result = article_processor.process_article(article_data)
            
            if not result["success"]:
                print(f"      ❌ Failed to process article")
                articles_failed += 1
                continue
            
            # Generate tags
            # Combine title and abstract for tag generation
            text_for_tags = f"{article_data.get('title', '')} {article_data.get('abstract', '')}"
            tags = tag_generator.generate_tags(
                text=text_for_tags,
                max_tags=15
            )
            category = tag_generator.generate_category(text_for_tags, tags)
            
            chunks_created = 0
            duplicates_skipped = 0
            
            print(f"      🔮 Generating embeddings for {len(result['chunks'])} chunks...")
            
            # Store chunks in MongoDB or TXT files
            for chunk_data in result["chunks"]:
                # Check for duplicates (only in normal mode with DB access)
                is_duplicate = False
                
                if check_duplicates and not settings.DRY_RUN and db is not None:
                    duplicate = await duplicate_detector.find_similar_chunk(
                        text=chunk_data["text"],
                        db=db,
                        source_type="article"
                    )
                    
                    if duplicate and duplicate["similarity"] >= similarity_threshold:
                        is_duplicate = True
                        duplicates_skipped += 1
                
                if not is_duplicate:
                    # Normalize title for pk
                    normalized_pk = "".join(
                        c if c.isalnum() else '-' 
                        for c in article_data.get("title", "unknown").lower()
                    ).strip('-')
                    # Remove consecutive hyphens
                    while '--' in normalized_pk:
                        normalized_pk = normalized_pk.replace('--', '-')
                    
                    # Generate embedding for the chunk
                    embedding = embedding_service.generate_embedding(chunk_data["text"])
                    
                    # Prepare chunk document
                    chunk_doc = {
                        "pk": normalized_pk,
                        "text": chunk_data["text"],
                        "source_type": "article",
                        "source_url": article_data.get("url", ""),
                        "embedding": embedding,  # Add embedding vector
                        "metadata": {
                            "article_metadata": result["metadata"],
                            "references": article_data.get("references", []),
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
                    
                    # DRY_RUN mode: save to TXT files instead of MongoDB
                    if settings.DRY_RUN:
                        # Create dry_runs/articles directory if it doesn't exist
                        dry_run_dir = Path("dry_runs/articles")
                        dry_run_dir.mkdir(parents=True, exist_ok=True)
                        
                        # Generate filename with timestamp
                        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
                        filename = f"{normalized_pk}-chunk-{chunk_data['chunk_index']}-{timestamp}.txt"
                        file_path = dry_run_dir / filename
                        
                        # Write chunk to file
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(f"PK: {normalized_pk}\n")
                            f.write(f"Chunk: {chunk_data['chunk_index'] + 1}/{chunk_data['total_chunks']}\n")
                            f.write(f"URL: {article_data.get('url', '')}\n")
                            f.write(f"Tags: {', '.join(tags)}\n")
                            f.write(f"Category: {category}\n")
                            if embedding:
                                f.write(f"Embedding: {len(embedding)} dimensions\n")
                                f.write(f"Embedding preview: [{', '.join(str(x) for x in embedding[:5])}...]\n")
                            f.write(f"{'='*70}\n\n")
                            f.write(chunk_data["text"])
                        
                        chunks_created += 1
                    else:
                        # Normal mode: Insert into MongoDB
                        await db.chunks.insert_one(chunk_doc)
                        chunks_created += 1
            
            total_chunks_created += chunks_created
            total_duplicates_skipped += duplicates_skipped
            articles_processed += 1
            
            print(f"      ✅ Created {chunks_created} chunks, skipped {duplicates_skipped} duplicates")
            
        except Exception as e:
            print(f"      ❌ Error processing article: {e}")
            articles_failed += 1
            continue
    
    # Summary
    print(f"\n{'='*70}")
    print(f"📊 PROCESSING SUMMARY")
    print(f"{'='*70}")
    print(f"   Total articles in file: {total_articles}")
    print(f"   Articles processed: {articles_processed}")
    print(f"   Articles failed: {articles_failed}")
    print(f"   Chunks created: {total_chunks_created}")
    print(f"   Duplicates skipped: {total_duplicates_skipped}")
    print(f"{'='*70}\n")
    
    return {
        "success": True,
        "total_articles": total_articles,
        "articles_processed": articles_processed,
        "articles_failed": articles_failed,
        "chunks_created": total_chunks_created,
        "duplicates_skipped": total_duplicates_skipped
    }


async def startup_initialization():
    """
    Main startup function
    Initializes MongoDB and loads articles from JSON files
    """
    print("\n" + "="*70)
    print("🚀 STARTING ETL SERVICE INITIALIZATION")
    print("="*70 + "\n")
    
    start_time = datetime.now()
    
    try:
        # Step 1: Ensure MongoDB collections
        await ensure_collections()
        
        # Step 2: Load articles from JSON file (if enabled)
        if settings.AUTO_LOAD_ARTICLES:
            # Show DRY_RUN mode status
            if settings.DRY_RUN:
                print("⚠️  DRY_RUN MODE ENABLED - Chunks will be saved to TXT files in dry_runs/articles/")
                print("   No data will be written to MongoDB")
            else:
                print("💾 NORMAL MODE - Chunks will be saved to MongoDB")
            
            articles_dir = Path("articles")
            articles_file_path = articles_dir / settings.ARTICLES_JSON_FILE
            
            print(f"📄 Loading articles from: {settings.ARTICLES_JSON_FILE}")
            
            if articles_file_path.exists():
                result = await load_articles_from_json(
                    articles_file_path,
                    check_duplicates=True,
                    similarity_threshold=0.95
                )
                
                if result.get("success"):
                    print(f"✅ Successfully loaded articles from {articles_file_path.name}")
                else:
                    print(f"⚠️  Failed to load articles: {result.get('error', 'Unknown error')}")
            else:
                print(f"⚠️  File '{settings.ARTICLES_JSON_FILE}' not found in {articles_dir}")
                print(f"   Skipping article loading...")
                print(f"   💡 Tip: Set ARTICLES_JSON_FILE in .env to change the source file")
        else:
            print("ℹ️  AUTO_LOAD_ARTICLES is disabled, skipping article loading")
            print("   To load articles manually, run: python scripts/load_articles.py")
        
        # Calculate duration
        duration = (datetime.now() - start_time).total_seconds()
        
        print("\n" + "="*70)
        print(f"✅ INITIALIZATION COMPLETED in {duration:.2f} seconds")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ INITIALIZATION FAILED: {e}")
        print("="*70 + "\n")
        raise


def run_startup():
    """Synchronous wrapper for startup initialization"""
    asyncio.run(startup_initialization())
