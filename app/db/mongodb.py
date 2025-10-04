from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from app.core.config import settings

# Async MongoDB client for FastAPI
motor_client: AsyncIOMotorClient = None
mongo_db = None

# Sync MongoDB client (if needed)
sync_client: MongoClient = None
sync_db = None


async def connect_to_mongo():
    """Connect to MongoDB using Motor (async driver)"""
    global motor_client, mongo_db
    
    try:
        print(f"🔌 Connecting to MongoDB...")
        print(f"📍 URL: {settings.MONGO_URL}")
        
        motor_client = AsyncIOMotorClient(settings.MONGO_URL, serverSelectionTimeoutMS=5000)
        mongo_db = motor_client[settings.MONGO_DB]
        
        # Test connection
        await motor_client.admin.command('ping')
        print(f"✅ Connected to MongoDB database: {settings.MONGO_DB}")
        print(f"📦 mongo_db object: {mongo_db}")
        
        return mongo_db
        
    except Exception as e:
        print(f"❌ Failed to connect to MongoDB: {e}")
        raise


async def close_mongo_connection():
    """Close MongoDB connection"""
    global motor_client
    if motor_client:
        motor_client.close()
        print("🔒 MongoDB connection closed")


def get_sync_mongo_client():
    """Get synchronous MongoDB client"""
    global sync_client, sync_db
    if sync_client is None:
        sync_client = MongoClient(settings.MONGO_URL)
        sync_db = sync_client[settings.MONGO_DB]
    return sync_db


async def get_mongo_db():
    """Dependency to get MongoDB database instance"""
    return mongo_db
