"""
Pydantic schemas for MongoDB collections: chunks and quotes
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId


class PyObjectId(ObjectId):
    """Custom ObjectId type for Pydantic"""
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema):
        field_schema.update(type="string")


class ChunkBase(BaseModel):
    """Base model for Chunk"""
    text: str = Field(..., description="Text content of the chunk")
    source: str = Field(..., description="Source of the chunk (URL, file, API, etc.)")
    source_type: str = Field(default="api", description="Type of source: api, file, web, etc.")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    embedding: Optional[List[float]] = Field(None, description="Vector embedding of the text")
    embedding_model: Optional[str] = Field(None, description="Model used to generate embedding")
    chunk_index: Optional[int] = Field(None, description="Index of chunk in original document")
    total_chunks: Optional[int] = Field(None, description="Total chunks from original document")


class ChunkCreate(ChunkBase):
    """Schema for creating a new chunk"""
    pass


class ChunkUpdate(BaseModel):
    """Schema for updating a chunk"""
    text: Optional[str] = None
    source: Optional[str] = None
    source_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    embedding: Optional[List[float]] = None
    embedding_model: Optional[str] = None
    chunk_index: Optional[int] = None
    total_chunks: Optional[int] = None


class ChunkInDB(ChunkBase):
    """Schema for chunk in database"""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str, datetime: lambda v: v.isoformat()}


class ChunkResponse(BaseModel):
    """Schema for chunk response"""
    id: str
    text: str
    source: str
    source_type: str
    metadata: Dict[str, Any]
    embedding_model: Optional[str] = None
    chunk_index: Optional[int] = None
    total_chunks: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    similarity_score: Optional[float] = None  # For search results

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class QuoteBase(BaseModel):
    """Base model for Quote"""
    text: str = Field(..., description="Quote text content")
    author: Optional[str] = Field(None, description="Author of the quote")
    source: Optional[str] = Field(None, description="Source of the quote")
    category: Optional[str] = Field(None, description="Category or topic")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    embedding: Optional[List[float]] = Field(None, description="Vector embedding of the quote")
    embedding_model: Optional[str] = Field(None, description="Model used to generate embedding")
    language: str = Field(default="en", description="Language code")


class QuoteCreate(QuoteBase):
    """Schema for creating a new quote"""
    pass


class QuoteUpdate(BaseModel):
    """Schema for updating a quote"""
    text: Optional[str] = None
    author: Optional[str] = None
    source: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    embedding: Optional[List[float]] = None
    embedding_model: Optional[str] = None
    language: Optional[str] = None


class QuoteInDB(QuoteBase):
    """Schema for quote in database"""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    views: int = Field(default=0, description="Number of times viewed")

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str, datetime: lambda v: v.isoformat()}


class QuoteResponse(BaseModel):
    """Schema for quote response"""
    id: str
    text: str
    author: Optional[str] = None
    source: Optional[str] = None
    category: Optional[str] = None
    tags: List[str]
    metadata: Dict[str, Any]
    embedding_model: Optional[str] = None
    language: str
    created_at: datetime
    updated_at: datetime
    views: int
    similarity_score: Optional[float] = None  # For search results

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class VectorSearchRequest(BaseModel):
    """Schema for vector similarity search request"""
    query: str = Field(..., description="Search query text")
    limit: int = Field(default=10, ge=1, le=100, description="Number of results to return")
    min_score: Optional[float] = Field(None, ge=0, le=1, description="Minimum similarity score")
    filters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional filters")


class VectorSearchResponse(BaseModel):
    """Schema for vector similarity search response"""
    query: str
    results: List[Any]  # Will be ChunkResponse or QuoteResponse
    count: int
    execution_time_ms: float
