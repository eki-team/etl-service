"""
API routes for chunks and quotes with vector search
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import datetime
from bson import ObjectId

from app.db.mongodb import get_mongo_db
from app.schemas.vectors import (
    ChunkCreate, ChunkUpdate, ChunkResponse,
    QuoteCreate, QuoteUpdate, QuoteResponse,
    VectorSearchRequest, VectorSearchResponse
)
from app.services.embeddings import embedding_service, VectorSearchService


router = APIRouter(prefix="/vectors", tags=["Vector Search"])


# ========== CHUNKS ENDPOINTS ==========

@router.post("/chunks", response_model=ChunkResponse, status_code=201)
async def create_chunk(
    chunk: ChunkCreate,
    generate_embedding: bool = Query(True, description="Auto-generate embedding"),
    db = Depends(get_mongo_db)
):
    """Create a new chunk with optional embedding generation"""
    
    chunk_data = chunk.model_dump()
    chunk_data["created_at"] = datetime.utcnow()
    chunk_data["updated_at"] = datetime.utcnow()
    
    # Generate embedding if requested
    if generate_embedding and not chunk_data.get("embedding"):
        embedding = embedding_service.generate_embedding(chunk_data["text"])
        if embedding:
            chunk_data["embedding"] = embedding
            chunk_data["embedding_model"] = embedding_service.model_name
    
    result = await db['chunks'].insert_one(chunk_data)
    chunk_data["id"] = str(result.inserted_id)
    
    return ChunkResponse(**chunk_data)


@router.get("/chunks", response_model=List[ChunkResponse])
async def list_chunks(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    source_type: Optional[str] = None,
    db = Depends(get_mongo_db)
):
    """List chunks with pagination and filtering"""
    
    query = {}
    if source_type:
        query["source_type"] = source_type
    
    cursor = db['chunks'].find(query).skip(skip).limit(limit).sort("created_at", -1)
    
    chunks = []
    async for chunk in cursor:
        chunk["id"] = str(chunk.pop("_id"))
        # Remove embedding from response for performance
        chunk.pop("embedding", None)
        chunks.append(ChunkResponse(**chunk))
    
    return chunks


@router.get("/chunks/{chunk_id}", response_model=ChunkResponse)
async def get_chunk(chunk_id: str, db = Depends(get_mongo_db)):
    """Get a specific chunk by ID"""
    
    if not ObjectId.is_valid(chunk_id):
        raise HTTPException(status_code=400, detail="Invalid chunk ID")
    
    chunk = await db['chunks'].find_one({"_id": ObjectId(chunk_id)})
    
    if not chunk:
        raise HTTPException(status_code=404, detail="Chunk not found")
    
    chunk["id"] = str(chunk.pop("_id"))
    chunk.pop("embedding", None)  # Remove embedding from response
    
    return ChunkResponse(**chunk)


@router.put("/chunks/{chunk_id}", response_model=ChunkResponse)
async def update_chunk(
    chunk_id: str,
    chunk_update: ChunkUpdate,
    regenerate_embedding: bool = Query(False, description="Regenerate embedding"),
    db = Depends(get_mongo_db)
):
    """Update a chunk"""
    
    if not ObjectId.is_valid(chunk_id):
        raise HTTPException(status_code=400, detail="Invalid chunk ID")
    
    update_data = {k: v for k, v in chunk_update.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.utcnow()
    
    # Regenerate embedding if text changed or explicitly requested
    if regenerate_embedding or (update_data.get("text")):
        existing_chunk = await db['chunks'].find_one({"_id": ObjectId(chunk_id)})
        if existing_chunk:
            text = update_data.get("text", existing_chunk.get("text"))
            embedding = embedding_service.generate_embedding(text)
            if embedding:
                update_data["embedding"] = embedding
                update_data["embedding_model"] = embedding_service.model_name
    
    result = await db['chunks'].find_one_and_update(
        {"_id": ObjectId(chunk_id)},
        {"$set": update_data},
        return_document=True
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="Chunk not found")
    
    result["id"] = str(result.pop("_id"))
    result.pop("embedding", None)
    
    return ChunkResponse(**result)


@router.delete("/chunks/{chunk_id}")
async def delete_chunk(chunk_id: str, db = Depends(get_mongo_db)):
    """Delete a chunk"""
    
    if not ObjectId.is_valid(chunk_id):
        raise HTTPException(status_code=400, detail="Invalid chunk ID")
    
    result = await db['chunks'].delete_one({"_id": ObjectId(chunk_id)})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Chunk not found")
    
    return {"message": "Chunk deleted successfully"}


@router.post("/chunks/search")
async def search_chunks(
    search_request: VectorSearchRequest,
    db = Depends(get_mongo_db)
):
    """Search chunks using vector similarity (cosine similarity)"""
    
    # Generate embedding for query
    query_embedding = embedding_service.generate_embedding(search_request.query)
    
    if not query_embedding:
        raise HTTPException(status_code=500, detail="Failed to generate query embedding")
    
    # Perform vector search
    results = await VectorSearchService.search_similar_chunks(
        db=db,
        query_embedding=query_embedding,
        limit=search_request.limit,
        min_score=search_request.min_score or 0.0,
        filters=search_request.filters
    )
    
    return {
        "query": search_request.query,
        "results": results["results"],
        "count": results["count"],
        "execution_time_ms": results["execution_time_ms"]
    }


# ========== QUOTES ENDPOINTS ==========

@router.post("/quotes", response_model=QuoteResponse, status_code=201)
async def create_quote(
    quote: QuoteCreate,
    generate_embedding: bool = Query(True, description="Auto-generate embedding"),
    db = Depends(get_mongo_db)
):
    """Create a new quote with optional embedding generation"""
    
    quote_data = quote.model_dump()
    quote_data["created_at"] = datetime.utcnow()
    quote_data["updated_at"] = datetime.utcnow()
    quote_data["views"] = 0
    
    # Generate embedding if requested
    if generate_embedding and not quote_data.get("embedding"):
        embedding = embedding_service.generate_embedding(quote_data["text"])
        if embedding:
            quote_data["embedding"] = embedding
            quote_data["embedding_model"] = embedding_service.model_name
    
    result = await db['quotes'].insert_one(quote_data)
    quote_data["id"] = str(result.inserted_id)
    
    return QuoteResponse(**quote_data)


@router.get("/quotes", response_model=List[QuoteResponse])
async def list_quotes(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    author: Optional[str] = None,
    category: Optional[str] = None,
    language: Optional[str] = None,
    db = Depends(get_mongo_db)
):
    """List quotes with pagination and filtering"""
    
    query = {}
    if author:
        query["author"] = author
    if category:
        query["category"] = category
    if language:
        query["language"] = language
    
    cursor = db['quotes'].find(query).skip(skip).limit(limit).sort("created_at", -1)
    
    quotes = []
    async for quote in cursor:
        quote["id"] = str(quote.pop("_id"))
        quote.pop("embedding", None)  # Remove embedding from response
        quotes.append(QuoteResponse(**quote))
    
    return quotes


@router.get("/quotes/{quote_id}", response_model=QuoteResponse)
async def get_quote(quote_id: str, db = Depends(get_mongo_db)):
    """Get a specific quote by ID and increment view count"""
    
    if not ObjectId.is_valid(quote_id):
        raise HTTPException(status_code=400, detail="Invalid quote ID")
    
    # Increment view count
    quote = await db['quotes'].find_one_and_update(
        {"_id": ObjectId(quote_id)},
        {"$inc": {"views": 1}},
        return_document=True
    )
    
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    quote["id"] = str(quote.pop("_id"))
    quote.pop("embedding", None)
    
    return QuoteResponse(**quote)


@router.put("/quotes/{quote_id}", response_model=QuoteResponse)
async def update_quote(
    quote_id: str,
    quote_update: QuoteUpdate,
    regenerate_embedding: bool = Query(False, description="Regenerate embedding"),
    db = Depends(get_mongo_db)
):
    """Update a quote"""
    
    if not ObjectId.is_valid(quote_id):
        raise HTTPException(status_code=400, detail="Invalid quote ID")
    
    update_data = {k: v for k, v in quote_update.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.utcnow()
    
    # Regenerate embedding if text changed or explicitly requested
    if regenerate_embedding or (update_data.get("text")):
        existing_quote = await db['quotes'].find_one({"_id": ObjectId(quote_id)})
        if existing_quote:
            text = update_data.get("text", existing_quote.get("text"))
            embedding = embedding_service.generate_embedding(text)
            if embedding:
                update_data["embedding"] = embedding
                update_data["embedding_model"] = embedding_service.model_name
    
    result = await db['quotes'].find_one_and_update(
        {"_id": ObjectId(quote_id)},
        {"$set": update_data},
        return_document=True
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    result["id"] = str(result.pop("_id"))
    result.pop("embedding", None)
    
    return QuoteResponse(**result)


@router.delete("/quotes/{quote_id}")
async def delete_quote(quote_id: str, db = Depends(get_mongo_db)):
    """Delete a quote"""
    
    if not ObjectId.is_valid(quote_id):
        raise HTTPException(status_code=400, detail="Invalid quote ID")
    
    result = await db['quotes'].delete_one({"_id": ObjectId(quote_id)})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    return {"message": "Quote deleted successfully"}


@router.post("/quotes/search")
async def search_quotes(
    search_request: VectorSearchRequest,
    db = Depends(get_mongo_db)
):
    """Search quotes using vector similarity (cosine similarity)"""
    
    # Generate embedding for query
    query_embedding = embedding_service.generate_embedding(search_request.query)
    
    if not query_embedding:
        raise HTTPException(status_code=500, detail="Failed to generate query embedding")
    
    # Perform vector search
    results = await VectorSearchService.search_similar_quotes(
        db=db,
        query_embedding=query_embedding,
        limit=search_request.limit,
        min_score=search_request.min_score or 0.0,
        filters=search_request.filters
    )
    
    return {
        "query": search_request.query,
        "results": results["results"],
        "count": results["count"],
        "execution_time_ms": results["execution_time_ms"]
    }


# ========== UTILITY ENDPOINTS ==========

@router.get("/stats")
async def get_stats(db = Depends(get_mongo_db)):
    """Get statistics about chunks and quotes collections"""
    
    chunks_count = await db['chunks'].count_documents({})
    chunks_with_embeddings = await db['chunks'].count_documents({"embedding": {"$ne": None}})
    
    quotes_count = await db['quotes'].count_documents({})
    quotes_with_embeddings = await db['quotes'].count_documents({"embedding": {"$ne": None}})
    
    return {
        "chunks": {
            "total": chunks_count,
            "with_embeddings": chunks_with_embeddings,
            "without_embeddings": chunks_count - chunks_with_embeddings
        },
        "quotes": {
            "total": quotes_count,
            "with_embeddings": quotes_with_embeddings,
            "without_embeddings": quotes_count - quotes_with_embeddings
        },
        "embedding_model": embedding_service.model_name,
        "embedding_dimensions": embedding_service.get_dimensions()
    }


@router.delete("/admin/clear-database", status_code=200)
async def clear_database(
    confirm: bool = Query(False, description="Must be True to confirm deletion"),
    db = Depends(get_mongo_db)
):
    """
    **DANGER**: Delete all data from chunks and quotes collections
    
    This endpoint will permanently delete all documents from both collections.
    Use with extreme caution in production environments.
    
    Parameters:
    - confirm: Must be set to True to proceed with deletion
    
    Returns:
    - Summary of deleted documents
    """
    
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Must set confirm=true to proceed with database deletion"
        )
    
    try:
        # Delete all documents from chunks collection
        chunks_result = await db['chunks'].delete_many({})
        chunks_deleted = chunks_result.deleted_count
        
        # Delete all documents from quotes collection
        quotes_result = await db['quotes'].delete_many({})
        quotes_deleted = quotes_result.deleted_count
        
        return {
            "success": True,
            "message": "Database cleared successfully",
            "deleted": {
                "chunks": chunks_deleted,
                "quotes": quotes_deleted,
                "total": chunks_deleted + quotes_deleted
            }
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error clearing database: {str(e)}"
        )
