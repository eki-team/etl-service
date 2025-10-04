"""
Service for processing scientific articles into chunks
"""
from typing import List, Dict, Any
from datetime import datetime
from app.services.chunking_service import chunking_service


class ArticleProcessor:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.chunking_service = chunking_service
    
    def process_article(self, article_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a scientific article into chunks
        
        Args:
            article_data: Article data dictionary
            
        Returns:
            Processing result with chunks
        """
        try:
            # Extract and combine text from article
            text_parts = []
            
            # Add title
            if article_data.get("title"):
                text_parts.append(f"Title: {article_data['title']}")
            
            # Add authors
            if article_data.get("authors"):
                authors_str = ", ".join(article_data["authors"])
                text_parts.append(f"Authors: {authors_str}")
            
            # Add abstract
            if article_data.get("abstract"):
                text_parts.append(f"Abstract: {article_data['abstract']}")
            
            # Add full text content
            if article_data.get("full_text", {}).get("full_content"):
                full_content = article_data["full_text"]["full_content"]
                if isinstance(full_content, list):
                    text_parts.extend(full_content)
                else:
                    text_parts.append(str(full_content))
            
            # Combine all text
            full_text = "\n\n".join(text_parts)
            cleaned_text = self.chunking_service.clean_text(full_text)
            
            # Create chunks using chunking service
            chunks = self.chunking_service.create_chunks(
                cleaned_text,
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap
            )
            
            # Calculate statistics
            total_chars = len(cleaned_text)
            total_words = len(cleaned_text.split())
            
            return {
                "success": True,
                "full_text": cleaned_text,
                "chunks": chunks,
                "total_chars": total_chars,
                "total_words": total_words,
                "metadata": {
                    "url": article_data.get("url", ""),
                    "title": article_data.get("title", ""),
                    "authors": article_data.get("authors", []),
                    "scraped_at": article_data.get("scraped_at", ""),
                    "pmc_id": article_data.get("original_data", {}).get("pmc_id", ""),
                    "doi": article_data.get("original_data", {}).get("doi", ""),
                    "statistics": article_data.get("statistics", {})
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "full_text": "",
                "chunks": [],
                "total_chars": 0,
                "total_words": 0,
                "metadata": {}
            }


# Global instance
article_processor = ArticleProcessor()
