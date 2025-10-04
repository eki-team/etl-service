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
    """Connect to MongoDB using Motor (async driver) with optimized Atlas settings"""
    global motor_client, mongo_db
    
    # Skip MongoDB connection if DRY_RUN is enabled
    if settings.DRY_RUN:
        print("⚠️  DRY_RUN MODE: Skipping MongoDB connection")
        print("   Data will be saved to TXT files instead")
        mongo_db = None
        return None
    
    try:
        print(f"🔌 Connecting to MongoDB Atlas...")
        print(f"📍 Cluster: nasakb.yvrx6cs.mongodb.net")
        print(f"💾 Database: {settings.MONGO_DB}")
        
        # Optimized configuration for MongoDB Atlas
        motor_client = AsyncIOMotorClient(
            settings.MONGO_URL,
            serverSelectionTimeoutMS=30000,  # 30 seconds timeout (increased from 5s)
            connectTimeoutMS=30000,           # 30 seconds connection timeout
            socketTimeoutMS=60000,            # 60 seconds socket timeout
            maxPoolSize=50,                   # Max connections in pool
            retryWrites=True,                 # Enable retry writes
            w='majority',                     # Write concern
            tlsAllowInvalidCertificates=False # Validate SSL certificates
        )
        
        mongo_db = motor_client[settings.MONGO_DB]
        
        # Test connection with retry
        print("⏳ Testing connection (this may take a few seconds)...")
        await motor_client.admin.command('ping')
        
        # Get server info
        server_info = await motor_client.server_info()
        print(f"✅ Successfully connected to MongoDB Atlas!")
        print(f"   MongoDB Version: {server_info.get('version', 'unknown')}")
        print(f"   Database: {settings.MONGO_DB}")
        
        return mongo_db
        
    except Exception as e:
        print(f"\n❌ Failed to connect to MongoDB Atlas:")
        print(f"   Error: {e}")
        print(f"\n🔍 Troubleshooting:")
        print(f"   1. Check if your IP is whitelisted in MongoDB Atlas")
        print(f"   2. Go to: https://cloud.mongodb.com/")
        print(f"   3. Network Access → Add IP Address → Add Current IP")
        print(f"   4. Or allow all IPs (dev only): 0.0.0.0/0")
        print(f"   5. Verify credentials are correct")
        raise


async def close_mongo_connection():
    """Close MongoDB connection"""
    global motor_client
    if motor_client:
        motor_client.close()
        print("🔒 MongoDB connection closed")


def get_sync_mongo_client():
    """Get synchronous MongoDB client with Atlas-optimized settings"""
    global sync_client, sync_db
    if sync_client is None:
        sync_client = MongoClient(
            settings.MONGO_URL,
            serverSelectionTimeoutMS=30000,
            connectTimeoutMS=30000,
            socketTimeoutMS=60000,
            maxPoolSize=50,
            retryWrites=True,
            w='majority'
        )
        sync_db = sync_client[settings.MONGO_DB]
    return sync_db


async def get_mongo_db():
    """Dependency to get MongoDB database instance"""
    if settings.DRY_RUN:
        return None
    return mongo_db
