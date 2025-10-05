"""
Service for generating embeddings using OpenAI API
"""
from typing import List, Dict, Any, Optional
import numpy as np
from datetime import datetime
import time
from openai import OpenAI
from app.core.config import settings


class EmbeddingService:
    """Service for generating text embeddings using OpenAI API"""
    
    def __init__(self):
        """Initialize OpenAI embedding service"""
        self.model_name = settings.OPENAI_EMBEDDING_MODEL
        self.batch_size = settings.OPENAI_BATCH_SIZE
        self.openai_client = None
        self._init_openai()
    
    def _init_openai(self):
        """Initialize OpenAI client"""
        try:
            if not settings.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY not configured in .env file")
            
            print(f"🔑 Initializing OpenAI API")
            print(f"   Model: {settings.OPENAI_EMBEDDING_MODEL}")
            print(f"   Dimensions: {settings.OPENAI_EMBEDDING_DIMENSIONS}")
            print(f"   Batch Size: {settings.OPENAI_BATCH_SIZE}")
            
            self.openai_client = OpenAI(
                api_key=settings.OPENAI_API_KEY,
                timeout=settings.OPENAI_TIMEOUT,
                max_retries=settings.OPENAI_MAX_RETRIES
            )
            print(f"✅ OpenAI API initialized successfully")
            
        except ImportError:
            raise ImportError("openai package not installed. Install with: pip install openai")
        except Exception as e:
            raise RuntimeError(f"Error initializing OpenAI: {e}")
    
    def generate_embedding(self, text: str, retry_count: int = 0) -> Optional[List[float]]:
        """
        Generate embedding vector for text using OpenAI API with automatic retry
        
        Args:
            text: Input text to embed
            retry_count: Current retry attempt
            
        Returns:
            List of floats representing the embedding vector, or None if error
        """
        if not self.openai_client:
            print("❌ OpenAI client not initialized")
            return None
        
        try:
            # Truncate text if too long (OpenAI has token limits)
            max_tokens = 8000  # Conservative limit
            if len(text) > max_tokens * 4:  # Rough estimate: 1 token ≈ 4 chars
                text = text[:max_tokens * 4]
            
            response = self.openai_client.embeddings.create(
                model=settings.OPENAI_EMBEDDING_MODEL,
                input=text,
                dimensions=settings.OPENAI_EMBEDDING_DIMENSIONS
            )
            
            return response.data[0].embedding
            
        except Exception as e:
            error_msg = str(e)
            
            # Handle rate limit errors with exponential backoff
            if "rate_limit" in error_msg.lower() or "429" in error_msg:
                if retry_count < settings.OPENAI_MAX_RETRIES:
                    # Extract wait time from error message
                    wait_time = 1.0  # Default 1 second
                    if "try again in" in error_msg.lower():
                        import re
                        match = re.search(r'try again in (\d+)ms', error_msg)
                        if match:
                            wait_time = int(match.group(1)) / 1000.0
                    
                    wait_time = wait_time * (2 ** retry_count)  # Exponential backoff
                    print(f"   ⏳ Rate limit hit, waiting {wait_time:.1f}s... (retry {retry_count + 1}/{settings.OPENAI_MAX_RETRIES})")
                    time.sleep(wait_time)
                    return self.generate_embedding(text, retry_count + 1)
            
            print(f"❌ Error generating OpenAI embedding: {e}")
            return None
    
    def generate_embeddings_batch(self, texts: List[str], batch_size: int = None, retry_count: int = 0) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts with intelligent rate limit handling
        
        Args:
            texts: List of texts to embed
            batch_size: Number of texts to process at once (default: from settings)
            retry_count: Current retry attempt
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        if not self.openai_client:
            print("❌ OpenAI client not initialized")
            return [None] * len(texts)
        
        # Use configured batch size if not specified
        if batch_size is None:
            batch_size = self.batch_size
        
        all_embeddings = []
        total_batches = (len(texts) - 1) // batch_size + 1
        
        try:
            # Process in batches with rate limit awareness
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                batch_num = i // batch_size + 1
                
                # Truncate texts if needed
                max_tokens = 8000
                truncated_batch = [
                    text[:max_tokens * 4] if len(text) > max_tokens * 4 else text
                    for text in batch
                ]
                
                print(f"   ⚡ Batch {batch_num}/{total_batches}: Processing {len(batch)} embeddings...")
                start_time = time.time()
                
                # Retry logic for rate limits
                success = False
                current_retry = 0
                
                while not success and current_retry <= settings.OPENAI_MAX_RETRIES:
                    try:
                        response = self.openai_client.embeddings.create(
                            model=settings.OPENAI_EMBEDDING_MODEL,
                            input=truncated_batch,
                            dimensions=settings.OPENAI_EMBEDDING_DIMENSIONS
                        )
                        
                        batch_embeddings = [item.embedding for item in response.data]
                        all_embeddings.extend(batch_embeddings)
                        success = True
                        
                    except Exception as batch_error:
                        error_msg = str(batch_error)
                        
                        # Handle rate limit with exponential backoff
                        if "rate_limit" in error_msg.lower() or "429" in error_msg:
                            if current_retry < settings.OPENAI_MAX_RETRIES:
                                # Extract wait time from error message
                                wait_time = 1.0
                                if "try again in" in error_msg.lower():
                                    import re
                                    match = re.search(r'try again in (\d+)ms', error_msg)
                                    if match:
                                        wait_time = int(match.group(1)) / 1000.0
                                
                                # Add exponential backoff
                                wait_time = wait_time + (0.5 * (2 ** current_retry))
                                print(f"   ⏳ Rate limit hit, waiting {wait_time:.1f}s... (retry {current_retry + 1}/{settings.OPENAI_MAX_RETRIES})")
                                time.sleep(wait_time)
                                current_retry += 1
                            else:
                                raise batch_error
                        else:
                            raise batch_error
                
                elapsed = time.time() - start_time
                rate = len(batch) / elapsed if elapsed > 0 else 0
                print(f"   ✅ Completed in {elapsed:.2f}s ({rate:.1f} embeddings/sec)")
                
                # Small delay between batches to avoid hitting rate limits
                if batch_num < total_batches:
                    time.sleep(0.6)  # 600ms as suggested by OpenAI
            
            return all_embeddings
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Error generating OpenAI embeddings batch: {e}")
            
            # If batch is too large (tokens exceeded), retry with smaller size
            if any(keyword in error_msg.lower() for keyword in [
                "too many", "too_many", "max_tokens", "tokens", "400"
            ]):
                new_batch_size = max(batch_size // 2, 10)
                print(f"   ⚠️  Batch too large, retrying with batch_size={new_batch_size}...")
                if retry_count < 5:  # Max 5 retries
                    return self.generate_embeddings_batch(texts, batch_size=new_batch_size, retry_count=retry_count + 1)
            
            return [None] * len(texts)
    
    def get_dimensions(self) -> int:
        """Get the dimensionality of embeddings"""
        return settings.OPENAI_EMBEDDING_DIMENSIONS


class VectorSearchService:
    """Service for vector similarity search"""
    
    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors
        
        Args:
            vec1: First vector
            vec2: Second vector
            
        Returns:
            Cosine similarity score (0 to 1)
        """
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        
        dot_product = np.dot(v1, v2)
        norm_v1 = np.linalg.norm(v1)
        norm_v2 = np.linalg.norm(v2)
        
        if norm_v1 == 0 or norm_v2 == 0:
            return 0.0
        
        similarity = dot_product / (norm_v1 * norm_v2)
        # Ensure similarity is in [0, 1] range
        return max(0.0, min(1.0, (similarity + 1) / 2))
    
    @staticmethod
    async def search_similar_chunks(
        db,
        query_embedding: List[float],
        limit: int = 10,
        min_score: float = 0.0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar chunks using vector similarity
        
        Args:
            db: MongoDB database instance
            query_embedding: Query embedding vector
            limit: Maximum number of results
            min_score: Minimum similarity score
            filters: Additional MongoDB filters
            
        Returns:
            List of matching chunks with similarity scores
        """
        start_time = time.time()
        
        # Build query
        query = filters or {}
        
        # Get all chunks with embeddings
        chunks_collection = db['chunks']
        cursor = chunks_collection.find(
            {**query, "embedding": {"$ne": None}},
            {"text": 1, "source": 1, "source_type": 1, "metadata": 1, 
             "embedding": 1, "embedding_model": 1, "chunk_index": 1, 
             "total_chunks": 1, "created_at": 1, "updated_at": 1}
        )
        
        results = []
        async for chunk in cursor:
            if chunk.get("embedding"):
                # Calculate similarity
                similarity = VectorSearchService.cosine_similarity(
                    query_embedding,
                    chunk["embedding"]
                )
                
                if similarity >= min_score:
                    chunk["similarity_score"] = similarity
                    chunk["id"] = str(chunk.pop("_id"))
                    results.append(chunk)
        
        # Sort by similarity score
        results.sort(key=lambda x: x["similarity_score"], reverse=True)
        
        # Limit results
        results = results[:limit]
        
        execution_time = (time.time() - start_time) * 1000
        
        return {
            "results": results,
            "count": len(results),
            "execution_time_ms": execution_time
        }
    
    @staticmethod
    async def search_similar_quotes(
        db,
        query_embedding: List[float],
        limit: int = 10,
        min_score: float = 0.0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar quotes using vector similarity
        
        Args:
            db: MongoDB database instance
            query_embedding: Query embedding vector
            limit: Maximum number of results
            min_score: Minimum similarity score
            filters: Additional MongoDB filters
            
        Returns:
            List of matching quotes with similarity scores
        """
        start_time = time.time()
        
        # Build query
        query = filters or {}
        
        # Get all quotes with embeddings
        quotes_collection = db['quotes']
        cursor = quotes_collection.find(
            {**query, "embedding": {"$ne": None}},
            {"text": 1, "author": 1, "source": 1, "category": 1, "tags": 1,
             "metadata": 1, "embedding": 1, "embedding_model": 1, "language": 1,
             "created_at": 1, "updated_at": 1, "views": 1}
        )
        
        results = []
        async for quote in cursor:
            if quote.get("embedding"):
                # Calculate similarity
                similarity = VectorSearchService.cosine_similarity(
                    query_embedding,
                    quote["embedding"]
                )
                
                if similarity >= min_score:
                    quote["similarity_score"] = similarity
                    quote["id"] = str(quote.pop("_id"))
                    results.append(quote)
        
        # Sort by similarity score
        results.sort(key=lambda x: x["similarity_score"], reverse=True)
        
        # Limit results
        results = results[:limit]
        
        execution_time = (time.time() - start_time) * 1000
        
        return {
            "results": results,
            "count": len(results),
            "execution_time_ms": execution_time
        }


# Global embedding service instance
embedding_service = EmbeddingService()
