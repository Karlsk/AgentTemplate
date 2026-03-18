"""RAG database models.

Only stores business-level metadata (knowledge base, document).
Chunk / embedding storage is managed by LlamaIndex PGVectorStore.
"""

from typing import Optional

from sqlalchemy import BigInteger, Text
from sqlmodel import Field

from app.models.base import BaseModel


class KnowledgeBaseModel(BaseModel, table=True):
    """Knowledge base, scoped to a workspace.

    Attributes:
        id: Primary key.
        workspace_id: Owning workspace.
        name: KB display name (unique within workspace).
        description: Free-text description.
        embedding_model_id: Optional FK to ai_model (embedding type).
        chunk_method: Chunking strategy (naive / sentence / token / delimiter).
        chunk_size: Target chunk size in characters.
        chunk_overlap: Overlap between chunks.
        retrieval_mode: Default retrieval mode (vector / hybrid).
        semantic_weight: Hybrid search semantic weight.
        keyword_weight: Hybrid search keyword weight.
        default_top_k: Default search top_k.
        enable_score_threshold: Whether score threshold is enabled.
        default_score_threshold: Default score threshold value.
        status: 0=inactive, 1=active, 2=indexing.
        doc_count: Cached document count.
        chunk_count: Cached chunk count.
    """

    __tablename__ = "rag_knowledge_base"

    id: int = Field(default=None, primary_key=True)
    workspace_id: int = Field(nullable=False, sa_type=BigInteger(), index=True)
    name: str = Field(max_length=255, nullable=False)
    description: str = Field(default="", sa_type=Text())
    embedding_model_id: Optional[int] = Field(default=None, nullable=True)
    chunk_method: str = Field(default="naive", max_length=32, nullable=False)
    chunk_size: int = Field(default=512, nullable=False)
    chunk_overlap: int = Field(default=64, nullable=False)
    retrieval_mode: str = Field(
        default="hybrid", max_length=32, nullable=False)
    semantic_weight: float = Field(default=0.7, nullable=False)
    keyword_weight: float = Field(default=0.3, nullable=False)
    default_top_k: int = Field(default=5, nullable=False)
    enable_score_threshold: bool = Field(default=False, nullable=False)
    default_score_threshold: float = Field(default=0.0, nullable=False)
    status: int = Field(default=1, nullable=False)
    doc_count: int = Field(default=0, nullable=False)
    chunk_count: int = Field(default=0, nullable=False)


class DocumentModel(BaseModel, table=True):
    """Uploaded document within a knowledge base.

    Attributes:
        id: Primary key.
        kb_id: FK to rag_knowledge_base.
        workspace_id: Denormalised for fast filtering.
        name: Original filename.
        file_path: Server-side file path.
        file_type: Extension (pdf, txt, docx, md, html, csv).
        file_size: Bytes.
        chunk_method: Per-doc chunk method override (None = use KB default).
        chunk_size: Per-doc chunk size override (None = use KB default).
        chunk_overlap: Per-doc overlap override (None = use KB default).
        chunk_separator: Custom delimiter for delimiter strategy.
        chunk_count: Number of chunks produced.
        status: 0=pending, 1=processing, 2=completed, 3=failed.
        error_msg: Error detail on failure.
        processing_step: Current step (parsing/chunking/embedding/completed/failed).
        parse_progress: Parse progress 0-100.
        chunk_progress: Chunk progress 0-100.
        embed_progress: Embed progress 0-100.
    """

    __tablename__ = "rag_document"

    id: int = Field(default=None, primary_key=True)
    kb_id: int = Field(nullable=False, index=True)
    workspace_id: int = Field(nullable=False, sa_type=BigInteger(), index=True)
    name: str = Field(max_length=512, nullable=False)
    file_path: str = Field(max_length=1024, nullable=False)
    file_type: str = Field(max_length=20, nullable=False)
    file_size: int = Field(default=0, nullable=False)
    chunk_method: Optional[str] = Field(
        default=None, max_length=32, nullable=True)
    chunk_size: Optional[int] = Field(default=None, nullable=True)
    chunk_overlap: Optional[int] = Field(default=None, nullable=True)
    chunk_separator: Optional[str] = Field(
        default=None, max_length=255, nullable=True)
    chunk_count: int = Field(default=0, nullable=False)
    status: int = Field(default=0, nullable=False)
    error_msg: Optional[str] = Field(default=None, sa_type=Text())
    processing_step: Optional[str] = Field(
        default=None, max_length=32, nullable=True)
    parse_progress: int = Field(default=0, nullable=False)
    chunk_progress: int = Field(default=0, nullable=False)
    embed_progress: int = Field(default=0, nullable=False)
