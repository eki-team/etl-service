"""
Service for chunking text into smaller pieces
"""
import re
from typing import List, Dict, Any


class ChunkingService:
    """Service to split text into overlapping chunks"""
    
    def __init__(self, chunk_size: int = 1500, chunk_overlap: int = 400):
        """
        Initialize chunking service with improved defaults for scientific content
        
        Args:
            chunk_size: Size of each chunk in characters (default: 1500)
            chunk_overlap: Overlap between chunks in characters (default: 400, ~26%)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove multiple whitespaces
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s\.\,\;\:\!\?\-\(\)\[\]\{\}]', '', text)
        return text.strip()
    
    def split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        # Simple sentence splitter
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def create_chunks(self, text: str, chunk_size: int = None, chunk_overlap: int = None) -> List[Dict[str, Any]]:
        """
        Split text into overlapping chunks with improved overlap consistency
        
        Args:
            text: Text to chunk
            chunk_size: Override default chunk size
            chunk_overlap: Override default overlap
            
        Returns:
            List of chunk dictionaries with metadata
        """
        # Use provided sizes or defaults
        size = chunk_size if chunk_size is not None else self.chunk_size
        overlap = chunk_overlap if chunk_overlap is not None else self.chunk_overlap
        
        if not text or len(text) < size:
            return [{
                "text": text,
                "chunk_index": 0,
                "total_chunks": 1,
                "char_count": len(text),
                "word_count": len(text.split()),
                "sentences": self.split_into_sentences(text)
            }]
        
        chunks = []
        start = 0
        chunk_index = 0
        previous_end = 0
        
        while start < len(text):
            # Calculate end position
            end = min(start + size, len(text))
            chunk_text = text[start:end]
            actual_end = end
            
            # Try to break at sentence boundary if not the last chunk
            if end < len(text):
                last_period = chunk_text.rfind('.')
                last_question = chunk_text.rfind('?')
                last_exclamation = chunk_text.rfind('!')
                
                break_point = max(last_period, last_question, last_exclamation)
                
                # Only adjust if we found a sentence end and it's not too close to the start
                if break_point > size * 0.5:  # At least 50% of chunk size
                    actual_end = start + break_point + 1
                    chunk_text = text[start:actual_end]
            
            sentences = self.split_into_sentences(chunk_text)
            
            chunks.append({
                "text": chunk_text.strip(),
                "chunk_index": chunk_index,
                "char_count": len(chunk_text),
                "word_count": len(chunk_text.split()),
                "sentences": sentences,
                "start_pos": start,
                "end_pos": actual_end
            })
            
            # Calculate next start position with guaranteed overlap
            if actual_end < len(text):
                # Start next chunk with overlap from the ACTUAL end of this chunk
                overlap_start = max(0, actual_end - overlap)
                
                # Try to start at a sentence boundary within the overlap region
                overlap_text = text[overlap_start:actual_end]
                
                # Find first sentence start in overlap region
                first_period = overlap_text.find('. ')
                first_question = overlap_text.find('? ')
                first_exclamation = overlap_text.find('! ')
                
                # Get valid sentence starts (not -1)
                valid_starts = [x for x in [first_period, first_question, first_exclamation] if x != -1]
                
                if valid_starts:
                    # Start at first sentence boundary in overlap
                    sentence_start = min(valid_starts)
                    start = overlap_start + sentence_start + 2  # +2 to skip ". " or "? " or "! "
                else:
                    # No sentence boundary found, use the overlap start
                    start = overlap_start
                
                # Ensure we always move forward
                if start <= previous_end:
                    start = previous_end + 1
            else:
                start = actual_end
            
            previous_end = actual_end
            chunk_index += 1
        
        # Update total_chunks
        for chunk in chunks:
            chunk["total_chunks"] = len(chunks)
        
        return chunks


# Global instance
chunking_service = ChunkingService()
