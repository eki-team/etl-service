
from fastapi import FastAPI
from app.db.mongodb import connect_to_mongo, close_mongo_connection, mongo_db
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.routes import vectors, pdf, articles
from app.core.startup import startup_initialization
import os

app = FastAPI(
    title="NASA ETL Service API",
    description="ETL Service with Vector Search and PDF Processing for NASA data",
    version="1.0.0"
)

# Include API routes
app.include_router(vectors.router, prefix="/api/v1")
app.include_router(pdf.router, prefix="/api/v1")
app.include_router(articles.router, prefix="/api/v1")

@app.on_event("startup")
async def startup_db_client():
    """Connect to MongoDB and initialize data on startup"""
    await connect_to_mongo()
    # Run initialization: create collections and load articles
    await startup_initialization()

@app.on_event("shutdown")
async def shutdown_db_client():
    """Close MongoDB connection on shutdown"""
    await close_mongo_connection()

raw = os.getenv(
    "CORS_ORIGINS",
    "http://localhost,http://localhost:4200,https://savewater-frontend.onrender.com"
)

origins = [o.strip().rstrip("/") for o in raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "NASA ETL Service API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "health": "/health",
            "mongodb_status": "/mongodb/status",
            "mongodb_documents_count": "/mongodb/documents/count",
            "pdf_upload": "/api/v1/pdf/upload",
            "article_process": "/api/v1/articles/process",
            "vector_search": "/api/v1/vectors/chunks/search"
        }
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "NASA ETL Service",
        "database": "MongoDB"
    }

@app.get("/mongodb/status")
async def mongodb_status():
    """Check MongoDB connection status"""
    try:
        # Check if MongoDB is connected
        if mongo_db is None:
            return {
                "status": "disconnected",
                "message": "DRY_RUN mode enabled - MongoDB connection skipped",
                "database": None
            }
        
        # Ping MongoDB to check connection
        await mongo_db.command("ping")
        
        # Get database stats
        stats = await mongo_db.command("dbStats")
        
        return {
            "status": "connected",
            "database": mongo_db.name,
            "collections": stats.get("collections", 0),
            "data_size": stats.get("dataSize", 0),
            "storage_size": stats.get("storageSize", 0)
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

@app.get("/mongodb/documents/count")
async def get_documents_count():
    """Get count of documents in all collections"""
    try:
        # Check if MongoDB is connected
        if mongo_db is None:
            return {
                "status": "error",
                "error": "MongoDB not connected. DRY_RUN mode may be enabled.",
                "message": "Set DRY_RUN=false in .env and restart the service"
            }
        
        # Get all collection names
        collections = await mongo_db.list_collection_names()
        
        # Count documents in each collection
        counts = {}
        total_documents = 0
        
        for collection_name in collections:
            count = await mongo_db[collection_name].count_documents({})
            counts[collection_name] = count
            total_documents += count
        
        # Get chunks with embeddings
        chunks_total = counts.get("chunks", 0)
        chunks_with_embeddings = 0
        chunks_without_embeddings = 0
        
        if chunks_total > 0:
            chunks_with_embeddings = await mongo_db.chunks.count_documents({
                "embedding": {"$exists": True, "$ne": None}
            })
            chunks_without_embeddings = chunks_total - chunks_with_embeddings
        
        # Get unique articles (by pk)
        unique_articles = 0
        if chunks_total > 0:
            pipeline = [
                {"$group": {"_id": "$pk"}},
                {"$count": "total"}
            ]
            result = await mongo_db.chunks.aggregate(pipeline).to_list(1)
            if result:
                unique_articles = result[0].get("total", 0)
        
        return {
            "status": "success",
            "database": mongo_db.name,
            "collections": counts,
            "summary": {
                "total_documents": total_documents,
                "total_collections": len(collections),
                "chunks": {
                    "total": chunks_total,
                    "with_embeddings": chunks_with_embeddings,
                    "without_embeddings": chunks_without_embeddings,
                    "percentage_embedded": round((chunks_with_embeddings / chunks_total * 100), 2) if chunks_total > 0 else 0
                },
                "unique_articles": unique_articles
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }