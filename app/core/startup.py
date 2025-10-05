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
    Load and process articles from a JSON file using OPTIMIZED PIPELINE
    
    Pipeline stages:
    1. Extract text from all articles (parallel)
    2. Generate tags for all articles
    3. Generate embeddings in batches (2048 per batch)
    4. Insert all chunks in one operation
    
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
    
    # Initialize
    db = await get_mongo_db() if not settings.DRY_RUN else None
    article_processor = ArticleProcessor(chunk_size=1500, chunk_overlap=400)
    
    total_articles = len(articles_data)
    articles_processed = 0
    articles_failed = 0
    
    print(f"\n{'='*70}")
    print(f"🚀 OPTIMIZED PIPELINE PROCESSING")
    print(f"{'='*70}\n")
    
    # ============================================================
    # PHASE 1: Extract text and generate chunks from all articles
    # ============================================================
    print(f"📝 Phase 1: Extracting text from {total_articles} articles...")
    
    all_chunks_data = []  # Will store all chunk documents
    all_texts_to_embed = []  # Will store all texts for batch embedding
    
    for idx, article_data in enumerate(articles_data, 1):
        try:
            if idx % 100 == 0 or idx == total_articles:
                print(f"   Processing {idx}/{total_articles} articles...")
            
            # Process article into chunks
            result = article_processor.process_article(article_data)
            
            if not result["success"]:
                articles_failed += 1
                continue
            
            # Generate tags
            text_for_tags = f"{article_data.get('title', '')} {article_data.get('abstract', '')}"
            tags = tag_generator.generate_tags(text=text_for_tags, max_tags=15)
            category = tag_generator.generate_category(text_for_tags, tags)
            
            # Normalize title for pk
            normalized_pk = "".join(
                c if c.isalnum() else '-' 
                for c in article_data.get("title", "unknown").lower()
            ).strip('-')
            while '--' in normalized_pk:
                normalized_pk = normalized_pk.replace('--', '-')
            
            # Process each chunk
            for chunk_data in result["chunks"]:
                # Prepare text with metadata for embedding
                text_with_metadata = chunk_data["text"]
                if tags:
                    text_with_metadata += f"\n\nKeywords: {', '.join(tags)}"
                if category:
                    text_with_metadata += f"\nCategory: {category}"
                
                # Store for batch embedding later
                all_texts_to_embed.append(text_with_metadata)
                
                # Prepare chunk document (without embedding yet)
                chunk_doc = {
                    "pk": normalized_pk,
                    "text": chunk_data["text"],
                    "abstract": article_data.get("abstract", ""),
                    "publication_year": article_data.get("publication_year", None),
                    "source_type": "article",
                    "source_url": article_data.get("url", ""),
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
                
                all_chunks_data.append(chunk_doc)
            
            articles_processed += 1
            
        except Exception as e:
            print(f"      ❌ Error processing article: {e}")
            articles_failed += 1
            continue
    
    print(f"✅ Phase 1 Complete: Extracted {len(all_chunks_data)} chunks from {articles_processed} articles")
    
    # ============================================================
    # PHASE 2: Generate embeddings in BATCH (optimized)
    # ============================================================
    if settings.DRY_RUN:
        print(f"\n⏭️  Phase 2: SKIPPED - Embeddings not generated in DRY_RUN mode")
        all_embeddings = []
    else:
        print(f"\n🧠 Phase 2: Generating embeddings for {len(all_texts_to_embed)} chunks...")
        print(f"   Using batch size: {settings.OPENAI_BATCH_SIZE}")
        
        all_embeddings = embedding_service.generate_embeddings_batch(
            texts=all_texts_to_embed,
            batch_size=settings.OPENAI_BATCH_SIZE
        )
        
        print(f"✅ Phase 2 Complete: Generated {len(all_embeddings)} embeddings")
    
    # ============================================================
    # PHASE 3: Assign embeddings to chunks
    # ============================================================
    if settings.DRY_RUN:
        print(f"\n⏭️  Phase 3: SKIPPED - No embeddings to assign in DRY_RUN mode")
    else:
        print(f"\n🔗 Phase 3: Assigning embeddings to chunks...")
        
        for i, embedding in enumerate(all_embeddings):
            if embedding and i < len(all_chunks_data):
                all_chunks_data[i]["embedding"] = embedding
        
        chunks_with_embeddings = sum(1 for chunk in all_chunks_data if "embedding" in chunk)
        print(f"✅ Phase 3 Complete: {chunks_with_embeddings}/{len(all_chunks_data)} chunks have embeddings")
    
    # ============================================================
    # PHASE 4: Insert all chunks into MongoDB (or save to files)
    # ============================================================
    total_chunks_created = 0
    
    if settings.DRY_RUN:
        print(f"\n💾 Phase 4: Saving {len(all_chunks_data)} chunks to TXT files...")
        dry_run_dir = Path("dry_runs/articles")
        dry_run_dir.mkdir(parents=True, exist_ok=True)
        
        for chunk_doc in all_chunks_data:
            timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S-%f")
            filename = f"{chunk_doc['pk']}-chunk-{chunk_doc['chunk_index']}-{timestamp}.txt"
            file_path = dry_run_dir / filename
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"PK: {chunk_doc['pk']}\n")
                f.write(f"Chunk: {chunk_doc['chunk_index'] + 1}/{chunk_doc['total_chunks']}\n")
                f.write(f"URL: {chunk_doc.get('source_url', '')}\n")
                f.write(f"Publication Year: {chunk_doc.get('publication_year', 'N/A')}\n")
                f.write(f"Tags: {', '.join(chunk_doc['metadata'].get('tags', []))}\n")
                f.write(f"Category: {chunk_doc['metadata'].get('category', 'N/A')}\n")
                if "embedding" in chunk_doc:
                    f.write(f"Embedding: {len(chunk_doc['embedding'])} dimensions\n")
                    f.write(f"Embedding preview: [{', '.join(str(x) for x in chunk_doc['embedding'][:5])}...]\n")
                else:
                    f.write(f"Embedding: Not generated (DRY_RUN mode)\n")
                f.write(f"{'='*70}\n")
                if chunk_doc.get('abstract'):
                    f.write(f"\nABSTRACT:\n{chunk_doc['abstract']}\n")
                    f.write(f"{'='*70}\n")
                f.write(f"\nCHUNK TEXT:\n")
                f.write(chunk_doc["text"])
            
            total_chunks_created += 1
        
        print(f"✅ Phase 4 Complete: Saved {total_chunks_created} chunks to {dry_run_dir}")
    
    else:
        print(f"\n� Phase 4: Inserting {len(all_chunks_data)} chunks into MongoDB...")
        
        if all_chunks_data and db is not None:
            try:
                result = await db.chunks.insert_many(all_chunks_data, ordered=False)
                total_chunks_created = len(result.inserted_ids)
                print(f"✅ Phase 4 Complete: Inserted {total_chunks_created} chunks into MongoDB")
            except Exception as e:
                print(f"❌ Error inserting chunks: {e}")
                # Try inserting one by one as fallback
                print(f"   Trying individual inserts...")
                for chunk in all_chunks_data:
                    try:
                        await db.chunks.insert_one(chunk)
                        total_chunks_created += 1
                    except:
                        pass
                print(f"   Inserted {total_chunks_created}/{len(all_chunks_data)} chunks")
    
    # Summary
    print(f"\n{'='*70}")
    print(f"📊 FINAL SUMMARY")
    print(f"{'='*70}")
    print(f"   Total articles in file: {total_articles}")
    print(f"   Articles processed: {articles_processed}")
    print(f"   Articles failed: {articles_failed}")
    print(f"   Chunks created: {total_chunks_created}")
    print(f"   Chunks with embeddings: {chunks_with_embeddings}")
    print(f"   Success rate: {(articles_processed/total_articles*100):.1f}%")
    print(f"{'='*70}\n")
    
    return {
        "success": True,
        "total_articles": total_articles,
        "articles_processed": articles_processed,
        "articles_failed": articles_failed,
        "chunks_created": total_chunks_created,
        "chunks_with_embeddings": chunks_with_embeddings
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
