"""Pydantic schemas for the RAG API."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ==================== Knowledge Base ====================

class KnowledgeBaseCreate(BaseModel):
    """Create a knowledge base."""

    name: str = Field(..., max_length=255)
    description: str = Field(default="")
    embedding_model_id: Optional[int] = Field(default=None)
    chunk_method: str = Field(
        default="naive", description="naive / sentence / token / delimiter")
    chunk_size: int = Field(default=512, ge=64, le=4096)
    chunk_overlap: int = Field(default=64, ge=0, le=512)
    retrieval_mode: str = Field(
        default="hybrid", description="vector / hybrid")
    semantic_weight: float = Field(default=0.7, ge=0.0, le=1.0)
    keyword_weight: float = Field(default=0.3, ge=0.0, le=1.0)
    default_top_k: int = Field(default=5, ge=1, le=50)
    enable_score_threshold: bool = Field(default=False)
    default_score_threshold: float = Field(default=0.0, ge=0.0, le=1.0)


class KnowledgeBaseUpdate(BaseModel):
    """Update a knowledge base."""

    id: int
    name: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None
    embedding_model_id: Optional[int] = None
    chunk_method: Optional[str] = None
    chunk_size: Optional[int] = Field(default=None, ge=64, le=4096)
    chunk_overlap: Optional[int] = Field(default=None, ge=0, le=512)
    retrieval_mode: Optional[str] = None
    semantic_weight: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    keyword_weight: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    default_top_k: Optional[int] = Field(default=None, ge=1, le=50)
    enable_score_threshold: Optional[bool] = None
    default_score_threshold: Optional[float] = Field(
        default=None, ge=0.0, le=1.0)
    status: Optional[int] = None


class KnowledgeBaseResponse(BaseModel):
    """Full KB response."""

    id: int
    workspace_id: int
    name: str
    description: str
    embedding_model_id: Optional[int] = None
    chunk_method: str
    chunk_size: int
    chunk_overlap: int
    retrieval_mode: str
    semantic_weight: float
    keyword_weight: float
    default_top_k: int
    enable_score_threshold: bool
    default_score_threshold: float
    status: int
    doc_count: int
    chunk_count: int
    created_at: datetime


class KnowledgeBaseListItem(BaseModel):
    """KB list item (lighter)."""

    id: int
    name: str
    description: str
    chunk_method: str
    retrieval_mode: str
    status: int
    doc_count: int
    chunk_count: int
    created_at: datetime


# ==================== Document ====================

class DocumentResponse(BaseModel):
    """Full document response."""

    id: int
    kb_id: int
    name: str
    file_type: str
    file_size: int
    chunk_method: Optional[str] = None
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None
    chunk_separator: Optional[str] = None
    chunk_count: int
    status: int
    error_msg: Optional[str] = None
    processing_step: Optional[str] = None
    parse_progress: int = 0
    chunk_progress: int = 0
    embed_progress: int = 0
    created_at: datetime


class DocumentListItem(BaseModel):
    """Document list item."""

    id: int
    name: str
    file_type: str
    file_size: int
    chunk_count: int
    status: int
    processing_step: Optional[str] = None
    parse_progress: int = 0
    chunk_progress: int = 0
    embed_progress: int = 0
    created_at: datetime


class DocumentProgressResponse(BaseModel):
    """Lightweight progress polling response."""

    doc_id: int
    status: int
    processing_step: Optional[str] = None
    parse_progress: int = 0
    chunk_progress: int = 0
    embed_progress: int = 0
    error_msg: Optional[str] = None


# ==================== Chunk Preview ====================

class ChunkPreviewItem(BaseModel):
    """Single chunk in preview."""

    chunk_index: int
    content: str
    char_count: int
    metadata: Optional[Dict[str, Any]] = None


class ChunkPreviewResponse(BaseModel):
    """Paginated chunk preview response."""

    doc_id: int
    doc_name: str
    total_chunks: int
    chunks: List[ChunkPreviewItem]


# ==================== Search ====================

class RAGSearchRequest(BaseModel):
    """Search request body."""

    kb_ids: List[int] = Field(..., min_length=1)
    query: str = Field(..., min_length=1, max_length=2000)
    top_k: Optional[int] = Field(default=None, ge=1, le=50)
    search_mode: Optional[str] = Field(
        default=None, description="vector / keyword / hybrid")
    score_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    rerank: bool = Field(default=False)
    semantic_weight: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    keyword_weight: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class ChunkResult(BaseModel):
    """Single retrieved chunk."""

    chunk_id: str
    doc_id: Optional[int] = None
    kb_id: Optional[int] = None
    content: str
    score: float
    metadata: Optional[Dict[str, Any]] = None
    doc_name: Optional[str] = None


class RAGSearchResponse(BaseModel):
    """Search response."""

    query: str
    results: List[ChunkResult]
    total: int
    trace: Optional[Dict[str, Any]] = None
