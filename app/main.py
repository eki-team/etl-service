
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