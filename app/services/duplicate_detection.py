"""
Service for duplicate detection using vector similarity
"""
from typing import Optional, List, Dict, Any
import numpy as np
from app.services.embeddings import embedding_service


class DuplicateDetectionService:
    """Service to detect duplicate chunks using vector similarity"""
    
    def __init__(self, similarity_threshold: float = 0.95):
        """
        Initialize duplicate detection service
        
        Args:
            similarity_threshold: Cosine similarity threshold (0-1).
                                 Values above this are considered duplicates.
                                 Default 0.95 means 95% similar.
        """
        self.similarity_threshold = similarity_threshold
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        
        dot_product = np.dot(v1, v2)
        norm_v1 = np.linalg.norm(v1)
        norm_v2 = np.linalg.norm(v2)
        
        if norm_v1 == 0 or norm_v2 == 0:
            return 0.0
        
        return float(dot_product / (norm_v1 * norm_v2))
    
    async def find_similar_chunk(
        self,
        text: str,
        db,
        source_type: str = None,
        limit: int = 5
    ) -> Optional[Dict[str, Any]]:
        """
        Find if a similar chunk already exists in the database
        
        Args:
            text: Text to check for duplicates
            db: MongoDB database instance
            source_type: Filter by source type (pdf, article, etc.)
            limit: Maximum number of candidates to check
            
        Returns:
            Dictionary with duplicate info if found, None otherwise
        """
        # Generate embedding for the new text
        new_embedding = embedding_service.generate_embedding(text)
        
        if not new_embedding:
            return None
        
        # Build query
        query = {}
        if source_type:
            query["source_type"] = source_type
        
        # Get recent chunks to compare (we'll use text-based pre-filtering)
        # MongoDB doesn't have native vector search without Atlas Search
        # So we'll do a hybrid approach: get candidates and compute similarity
        
        candidates = []
        cursor = db['chunks'].find(query).sort("created_at", -1).limit(100)
        
        async for doc in cursor:
            candidates.append({
                "id": str(doc["_id"]),
                "text": doc["text"],
                "pk": doc.get("pk", ""),
                "source_type": doc.get("source_type", ""),
                "created_at": doc.get("created_at")
            })
        
        # Calculate similarity for each candidate
        similarities = []
        
        for candidate in candidates:
            candidate_embedding = embedding_service.generate_embedding(candidate["text"])
            
            if candidate_embedding:
                similarity = self.cosine_similarity(new_embedding, candidate_embedding)
                
                if similarity >= self.similarity_threshold:
                    similarities.append({
                        "chunk_id": candidate["id"],
                        "similarity": similarity,
                        "text_preview": candidate["text"][:100] + "...",
                        "pk": candidate["pk"],
                        "source_type": candidate["source_type"],
                        "created_at": candidate["created_at"]
                    })
        
        # Sort by similarity (highest first)
        similarities.sort(key=lambda x: x["similarity"], reverse=True)
        
        # Return the most similar if found
        if similarities:
            return similarities[0]
        
        return None
    
    async def check_duplicate_batch(
        self,
        texts: List[str],
        db,
        source_type: str = None
    ) -> List[Optional[Dict[str, Any]]]:
        """
        Check multiple texts for duplicates in batch
        
        Args:
            texts: List of texts to check
            db: MongoDB database instance
            source_type: Filter by source type
            
        Returns:
            List of duplicate info (or None) for each text
        """
        results = []
        
        for text in texts:
            duplicate = await self.find_similar_chunk(text, db, source_type)
            results.append(duplicate)
        
        return results


# Global instance
duplicate_detector = DuplicateDetectionService(similarity_threshold=0.95)
