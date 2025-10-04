"""
Schemas for scientific article processing
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class ArticleFullText(BaseModel):
    full_content: List[str] = Field(default_factory=list)


class ArticleStatistics(BaseModel):
    total_authors: int = 0
    abstract_words: int = 0
    total_words: int = 0
    references_count: int = 0
    sections_found: List[str] = Field(default_factory=list)


class ArticleOriginalData(BaseModel):
    pmc_id: Optional[str] = None
    doi: Optional[str] = None
    figures_count: int = 0
    tables_count: int = 0


class ArticleInput(BaseModel):
    url: str
    title: str
    authors: List[str] = Field(default_factory=list)
    abstract: str = ""
    full_text: ArticleFullText = Field(default_factory=ArticleFullText)
    references: List[Any] = Field(default_factory=list)
    statistics: ArticleStatistics = Field(default_factory=ArticleStatistics)
    scraped_at: str
    success: bool = True
    original_data: ArticleOriginalData = Field(default_factory=ArticleOriginalData)


class ArticleProcessResponse(BaseModel):
    success: bool
    article_title: str
    summary: Dict[str, Any]
    chunk_ids: List[str]
    metadata: Dict[str, Any]


class BatchArticleProcessResponse(BaseModel):
    success: bool
    total_articles: int
    successful: int
    failed: int
    total_chunks_created: int
    results: List[Dict[str, Any]]
    failed_articles: List[Dict[str, Any]]
