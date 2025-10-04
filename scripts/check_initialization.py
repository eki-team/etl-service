"""
Test script to verify startup initialization
Connects to MongoDB and checks if articles were loaded
"""
import asyncio
from app.db.mongodb import get_mongo_db


async def check_initialization():
    """Check if initialization was successful"""
    print("\n🔍 Checking initialization status...\n")
    
    async for db in get_mongo_db():
        # Check collections
        collections = await db.list_collection_names()
        print(f"📦 Collections found: {collections}")
        
        # Check chunks count
        chunks_count = await db.chunks.count_documents({})
        print(f"📊 Total chunks in database: {chunks_count}")
        
        # Check unique articles (by pk)
        unique_articles = await db.chunks.distinct("pk")
        print(f"📰 Unique articles: {len(unique_articles)}")
        
        # Show sample of categories
        pipeline = [
            {"$group": {"_id": "$metadata.category", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        categories = await db.chunks.aggregate(pipeline).to_list(None)
        
        print(f"\n📂 Articles by category:")
        for cat in categories:
            print(f"   - {cat['_id']}: {cat['count']} chunks")
        
        # Show sample article titles
        sample_docs = await db.chunks.find({}, {"pk": 1, "metadata.article_metadata.title": 1}).limit(5).to_list(5)
        
        print(f"\n📄 Sample articles (first 5):")
        for doc in sample_docs:
            title = doc.get("metadata", {}).get("article_metadata", {}).get("title", "No title")
            pk = doc.get("pk", "No pk")
            print(f"   - [{pk}] {title[:80]}...")
        
        break


if __name__ == "__main__":
    asyncio.run(check_initialization())
