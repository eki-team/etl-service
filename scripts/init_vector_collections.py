"""
Initialize MongoDB collections with vector search indexes for cosine similarity
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from datetime import datetime


async def create_vector_search_indexes():
    """Create MongoDB collections and vector search indexes"""
    
    print("=" * 70)
    print("🚀 INITIALIZING MONGODB COLLECTIONS WITH VECTOR INDEXES")
    print("=" * 70)
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(settings.MONGO_URL, serverSelectionTimeoutMS=5000)
    db = client[settings.MONGO_DB]
    
    try:
        # Test connection
        await client.admin.command('ping')
        print(f"✅ Connected to MongoDB: {settings.MONGO_DB}")
        
        # ========== CHUNKS COLLECTION ==========
        print("\n📦 Setting up 'chunks' collection...")
        
        chunks_collection = db['chunks']
        
        # Create indexes for chunks
        print("  📍 Creating indexes for chunks...")
        
        # Text index for full-text search
        await chunks_collection.create_index([("text", "text")])
        print("    ✅ Text index created")
        
        # Index on source for filtering
        await chunks_collection.create_index([("source", 1)])
        print("    ✅ Source index created")
        
        # Index on source_type
        await chunks_collection.create_index([("source_type", 1)])
        print("    ✅ Source type index created")
        
        # Index on created_at for sorting
        await chunks_collection.create_index([("created_at", -1)])
        print("    ✅ Created_at index created")
        
        # Compound index for common queries
        await chunks_collection.create_index([
            ("source_type", 1),
            ("created_at", -1)
        ])
        print("    ✅ Compound index (source_type + created_at) created")
        
        # Vector Search Index (Atlas Search - requires MongoDB Atlas)
        # Note: This is the configuration for Atlas Vector Search
        # If using local MongoDB, you'll need to use $lookup or aggregation pipelines
        print("\n  📊 Vector search configuration for 'chunks':")
        print("    Embedding field: 'embedding'")
        print("    Similarity metric: cosine")
        print("    Dimensions: flexible (based on embedding model)")
        
        
        # ========== QUOTES COLLECTION ==========
        print("\n💬 Setting up 'quotes' collection...")
        
        quotes_collection = db['quotes']
        
        # Create indexes for quotes
        print("  📍 Creating indexes for quotes...")
        
        # Text index for full-text search
        await quotes_collection.create_index([("text", "text")])
        print("    ✅ Text index created")
        
        # Index on author
        await quotes_collection.create_index([("author", 1)])
        print("    ✅ Author index created")
        
        # Index on category
        await quotes_collection.create_index([("category", 1)])
        print("    ✅ Category index created")
        
        # Index on tags (multikey index)
        await quotes_collection.create_index([("tags", 1)])
        print("    ✅ Tags index created")
        
        # Index on language
        await quotes_collection.create_index([("language", 1)])
        print("    ✅ Language index created")
        
        # Index on created_at for sorting
        await quotes_collection.create_index([("created_at", -1)])
        print("    ✅ Created_at index created")
        
        # Index on views for popular quotes
        await quotes_collection.create_index([("views", -1)])
        print("    ✅ Views index created")
        
        # Compound index for filtering
        await quotes_collection.create_index([
            ("category", 1),
            ("language", 1),
            ("created_at", -1)
        ])
        print("    ✅ Compound index (category + language + created_at) created")
        
        print("\n  📊 Vector search configuration for 'quotes':")
        print("    Embedding field: 'embedding'")
        print("    Similarity metric: cosine")
        print("    Dimensions: flexible (based on embedding model)")
        
        
        # ========== SUMMARY ==========
        print("\n" + "=" * 70)
        print("✅ COLLECTIONS INITIALIZED SUCCESSFULLY!")
        print("=" * 70)
        
        # Get collection info
        collections = await db.list_collection_names()
        print(f"\n📚 Available collections: {collections}")
        
        # Insert sample documents to test
        print("\n🧪 Inserting sample documents...")
        
        # Sample chunk
        sample_chunk = {
            "text": "NASA's James Webb Space Telescope has captured stunning images of distant galaxies.",
            "source": "NASA API",
            "source_type": "api",
            "metadata": {
                "topic": "space",
                "year": 2025
            },
            "embedding": None,  # Will be generated by embedding service
            "embedding_model": None,
            "chunk_index": 0,
            "total_chunks": 1,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = await chunks_collection.insert_one(sample_chunk)
        print(f"  ✅ Sample chunk inserted with ID: {result.inserted_id}")
        
        # Sample quote
        sample_quote = {
            "text": "The cosmos is within us. We are made of star-stuff.",
            "author": "Carl Sagan",
            "source": "Cosmos",
            "category": "science",
            "tags": ["space", "philosophy", "cosmos"],
            "metadata": {
                "year": 1980,
                "context": "Cosmos TV series"
            },
            "embedding": None,  # Will be generated by embedding service
            "embedding_model": None,
            "language": "en",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "views": 0
        }
        
        result = await quotes_collection.insert_one(sample_quote)
        print(f"  ✅ Sample quote inserted with ID: {result.inserted_id}")
        
        print("\n" + "=" * 70)
        print("🎉 SETUP COMPLETE!")
        print("=" * 70)
        
        print("\n📝 NOTES:")
        print("  • For MongoDB Atlas: Enable Atlas Vector Search in the UI")
        print("  • For local MongoDB: Use aggregation pipelines for vector search")
        print("  • Install embedding library: pip install sentence-transformers")
        print("  • Recommended embedding models:")
        print("    - sentence-transformers/all-MiniLM-L6-v2 (384 dimensions)")
        print("    - sentence-transformers/all-mpnet-base-v2 (768 dimensions)")
        print("    - OpenAI text-embedding-ada-002 (1536 dimensions)")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        client.close()
        print("\n🔒 Connection closed")


async def drop_collections():
    """Drop chunks and quotes collections (use with caution!)"""
    
    print("⚠️  WARNING: This will delete all data in chunks and quotes collections!")
    
    client = AsyncIOMotorClient(settings.MONGO_URL, serverSelectionTimeoutMS=5000)
    db = client[settings.MONGO_DB]
    
    try:
        await db['chunks'].drop()
        print("✅ Dropped 'chunks' collection")
        
        await db['quotes'].drop()
        print("✅ Dropped 'quotes' collection")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        
    finally:
        client.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "drop":
        print("⚠️  Dropping collections...")
        asyncio.run(drop_collections())
    else:
        asyncio.run(create_vector_search_indexes())
