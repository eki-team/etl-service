"""
Service for generating embeddings and performing vector similarity search
"""
from typing import List, Dict, Any, Optional
import numpy as np
from datetime import datetime
import time


class EmbeddingService:
    """Service for generating text embeddings"""
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """
        Initialize embedding service
        
        Args:
            model_name: Name of the embedding model to use
        """
        self.model_name = model_name
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load the embedding model"""
        try:
            from sentence_transformers import SentenceTransformer
            print(f"📦 Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            print(f"✅ Model loaded successfully")
        except ImportError:
            print("⚠️  sentence-transformers not installed")
            print("   Install with: pip install sentence-transformers")
            self.model = None
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            self.model = None
    
    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding vector for text
        
        Args:
            text: Input text to embed
            
        Returns:
            List of floats representing the embedding vector, or None if model not available
        """
        if self.model is None:
            # Return dummy embedding for testing without model
            return self._generate_dummy_embedding(text)
        
        try:
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            print(f"❌ Error generating embedding: {e}")
            return None
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        if self.model is None:
            return [self._generate_dummy_embedding(text) for text in texts]
        
        try:
            embeddings = self.model.encode(texts, convert_to_numpy=True)
            return [emb.tolist() for emb in embeddings]
        except Exception as e:
            print(f"❌ Error generating embeddings: {e}")
            return [None] * len(texts)
    
    def _generate_dummy_embedding(self, text: str, dimensions: int = 384) -> List[float]:
        """
        Generate a dummy embedding for testing (deterministic based on text)
        
        Args:
            text: Input text
            dimensions: Embedding dimensions
            
        Returns:
            Dummy embedding vector
        """
        # Use hash for deterministic dummy embeddings
        np.random.seed(hash(text) % (2**32))
        embedding = np.random.randn(dimensions)
        # Normalize to unit vector
        embedding = embedding / np.linalg.norm(embedding)
        return embedding.tolist()
    
    def get_dimensions(self) -> int:
        """Get the dimensionality of embeddings"""
        if self.model is None:
            return 384  # Default for all-MiniLM-L6-v2
        
        # Generate a test embedding to get dimensions
        test_embedding = self.generate_embedding("test")
        return len(test_embedding) if test_embedding else 384


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
