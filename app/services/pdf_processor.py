"""
Service for processing PDF documents into chunks
"""
import io
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
import PyPDF2
import pdfplumber


class PDFProcessor:
    """Service for extracting and processing text from PDF documents"""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Initialize PDF processor
        
        Args:
            chunk_size: Maximum size of each text chunk (in characters)
            chunk_overlap: Number of characters to overlap between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def extract_text_pypdf2(self, pdf_bytes: bytes) -> str:
        """
        Extract text from PDF using PyPDF2
        
        Args:
            pdf_bytes: PDF file content as bytes
            
        Returns:
            Extracted text
        """
        try:
            pdf_file = io.BytesIO(pdf_bytes)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            text_parts = []
            for page_num, page in enumerate(pdf_reader.pages):
                text = page.extract_text()
                if text:
                    text_parts.append(text)
            
            return "\n\n".join(text_parts)
            
        except Exception as e:
            print(f"❌ Error extracting text with PyPDF2: {e}")
            return ""
    
    def extract_text_pdfplumber(self, pdf_bytes: bytes) -> str:
        """
        Extract text from PDF using pdfplumber (better for complex PDFs)
        
        Args:
            pdf_bytes: PDF file content as bytes
            
        Returns:
            Extracted text
        """
        try:
            pdf_file = io.BytesIO(pdf_bytes)
            text_parts = []
            
            with pdfplumber.open(pdf_file) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
            
            return "\n\n".join(text_parts)
            
        except Exception as e:
            print(f"❌ Error extracting text with pdfplumber: {e}")
            return ""
    
    def extract_text(self, pdf_bytes: bytes, method: str = "pdfplumber") -> str:
        """
        Extract text from PDF using specified method
        
        Args:
            pdf_bytes: PDF file content as bytes
            method: Extraction method ('pypdf2' or 'pdfplumber')
            
        Returns:
            Extracted text
        """
        if method == "pypdf2":
            text = self.extract_text_pypdf2(pdf_bytes)
        else:
            text = self.extract_text_pdfplumber(pdf_bytes)
        
        # Fallback to alternative method if first fails
        if not text and method == "pdfplumber":
            print("⚠️  Trying PyPDF2 as fallback...")
            text = self.extract_text_pypdf2(pdf_bytes)
        elif not text and method == "pypdf2":
            print("⚠️  Trying pdfplumber as fallback...")
            text = self.extract_text_pdfplumber(pdf_bytes)
        
        return text
    
    def clean_text(self, text: str) -> str:
        """
        Clean and normalize extracted text
        
        Args:
            text: Raw extracted text
            
        Returns:
            Cleaned text
        """
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep punctuation
        text = re.sub(r'[^\w\s\.\,\!\?\;\:\-\(\)\[\]\{\}\"\'\/\\]', '', text)
        
        # Normalize newlines
        text = re.sub(r'\n+', '\n', text)
        
        # Strip whitespace
        text = text.strip()
        
        return text
    
    def split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences
        
        Args:
            text: Input text
            
        Returns:
            List of sentences
        """
        # Simple sentence splitter (can be improved with NLTK)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def create_chunks(self, text: str) -> List[Dict[str, Any]]:
        """
        Split text into overlapping chunks
        
        Args:
            text: Input text
            
        Returns:
            List of text chunks with metadata
        """
        # Clean text first
        text = self.clean_text(text)
        
        if not text:
            return []
        
        chunks = []
        sentences = self.split_into_sentences(text)
        
        current_chunk = ""
        current_sentences = []
        
        for sentence in sentences:
            # Check if adding this sentence would exceed chunk size
            if len(current_chunk) + len(sentence) + 1 > self.chunk_size and current_chunk:
                # Save current chunk
                chunks.append({
                    "text": current_chunk.strip(),
                    "sentences": current_sentences,
                    "char_count": len(current_chunk),
                    "word_count": len(current_chunk.split())
                })
                
                # Start new chunk with overlap
                overlap_text = current_chunk[-self.chunk_overlap:] if len(current_chunk) > self.chunk_overlap else current_chunk
                current_chunk = overlap_text + " " + sentence
                current_sentences = [sentence]
            else:
                # Add sentence to current chunk
                if current_chunk:
                    current_chunk += " " + sentence
                else:
                    current_chunk = sentence
                current_sentences.append(sentence)
        
        # Add the last chunk
        if current_chunk:
            chunks.append({
                "text": current_chunk.strip(),
                "sentences": current_sentences,
                "char_count": len(current_chunk),
                "word_count": len(current_chunk.split())
            })
        
        # Add chunk indices
        for idx, chunk in enumerate(chunks):
            chunk["chunk_index"] = idx
            chunk["total_chunks"] = len(chunks)
        
        return chunks
    
    def extract_metadata(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """
        Extract metadata from PDF
        
        Args:
            pdf_bytes: PDF file content as bytes
            
        Returns:
            PDF metadata
        """
        try:
            pdf_file = io.BytesIO(pdf_bytes)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            metadata = {
                "num_pages": len(pdf_reader.pages),
                "info": {}
            }
            
            # Extract document info
            if pdf_reader.metadata:
                info = pdf_reader.metadata
                metadata["info"] = {
                    "title": info.get("/Title", ""),
                    "author": info.get("/Author", ""),
                    "subject": info.get("/Subject", ""),
                    "creator": info.get("/Creator", ""),
                    "producer": info.get("/Producer", ""),
                    "creation_date": info.get("/CreationDate", ""),
                    "modification_date": info.get("/ModDate", "")
                }
            
            return metadata
            
        except Exception as e:
            print(f"⚠️  Error extracting metadata: {e}")
            return {"num_pages": 0, "info": {}}
    
    def process_pdf(
        self,
        pdf_bytes: bytes,
        filename: str,
        extraction_method: str = "pdfplumber"
    ) -> Dict[str, Any]:
        """
        Complete PDF processing pipeline
        
        Args:
            pdf_bytes: PDF file content as bytes
            filename: Original filename
            extraction_method: Text extraction method
            
        Returns:
            Processing results with chunks and metadata
        """
        print(f"📄 Processing PDF: {filename}")
        
        # Extract metadata
        metadata = self.extract_metadata(pdf_bytes)
        print(f"  📊 Pages: {metadata['num_pages']}")
        
        # Extract text
        print(f"  📝 Extracting text with {extraction_method}...")
        text = self.extract_text(pdf_bytes, method=extraction_method)
        
        if not text:
            return {
                "success": False,
                "error": "Failed to extract text from PDF",
                "filename": filename,
                "metadata": metadata
            }
        
        print(f"  ✅ Extracted {len(text)} characters")
        
        # Create chunks
        print(f"  ✂️  Creating chunks (size={self.chunk_size}, overlap={self.chunk_overlap})...")
        chunks = self.create_chunks(text)
        print(f"  ✅ Created {len(chunks)} chunks")
        
        return {
            "success": True,
            "filename": filename,
            "full_text": text,
            "chunks": chunks,
            "metadata": metadata,
            "total_chars": len(text),
            "total_words": len(text.split()),
            "total_chunks": len(chunks)
        }


# Global PDF processor instance
pdf_processor = PDFProcessor(chunk_size=1000, chunk_overlap=200)
