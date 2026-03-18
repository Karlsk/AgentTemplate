"""Ingestion pipeline: parse -> chunk -> embed -> store.

Orchestrates the full document ingestion flow using LlamaIndex components.
Supports model-specific batch_size with adaptive retry on batch failures.
"""

import time
from typing import Any, Dict, List, Optional

from llama_index.core.embeddings import BaseEmbedding
from llama_index.core.schema import BaseNode, TextNode
from sqlmodel import Session

from app.core.common.config import settings
from app.core.common.logging import TerraLogUtil
from app.core.rag.embedding.provider import DEFAULT_SAFE_BATCH_SIZE
from app.core.rag.ingestion.chunking import ChunkMethod, chunk_documents
from app.core.rag.ingestion.parser import parse_file
from app.models.rag import DocumentModel


class IngestionResult:
    """Container for the result of a pipeline run."""

    def __init__(
        self,
        nodes: List[BaseNode],
        trace: Dict[str, Any],
    ):
        """Initialize with processed nodes and timing trace."""
        self.nodes = nodes
        self.trace = trace

    @property
    def chunk_count(self) -> int:
        """Number of nodes produced."""
        return len(self.nodes)


def _update_progress(
    session: Optional[Session],
    doc_model: Optional[DocumentModel],
    step: Optional[str] = None,
    parse_progress: Optional[int] = None,
    chunk_progress: Optional[int] = None,
    embed_progress: Optional[int] = None,
) -> None:
    """Update document processing progress in the database."""
    if not session or not doc_model:
        return
    if step is not None:
        doc_model.processing_step = step
    if parse_progress is not None:
        doc_model.parse_progress = parse_progress
    if chunk_progress is not None:
        doc_model.chunk_progress = chunk_progress
    if embed_progress is not None:
        doc_model.embed_progress = embed_progress
    session.add(doc_model)
    session.commit()


async def run_ingestion(
    file_path: str,
    file_type: str,
    embed_model: BaseEmbedding,
    doc_id: int,
    kb_id: int,
    workspace_id: int,
    chunk_method: str = ChunkMethod.NAIVE,
    chunk_size: int = settings.RAG_DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = settings.RAG_DEFAULT_CHUNK_OVERLAP,
    batch_size: int = DEFAULT_SAFE_BATCH_SIZE,
    session: Optional[Session] = None,
    doc_model: Optional[DocumentModel] = None,
    **chunk_kwargs,
) -> IngestionResult:
    """Run the full ingestion pipeline on a single file.

    Steps:
        1. Parse file -> LlamaIndex Documents
        2. Chunk documents -> TextNode list
        3. Inject metadata (doc_id, kb_id, workspace_id)
        4. Compute embeddings via embed_model

    Args:
        file_path: Path to the uploaded file.
        file_type: Extension (pdf, txt, ...).
        embed_model: LlamaIndex BaseEmbedding instance.
        doc_id: DB document ID.
        kb_id: DB knowledge base ID.
        workspace_id: Workspace ID for tenant isolation.
        chunk_method: Chunking strategy.
        chunk_size: Target chunk size.
        chunk_overlap: Chunk overlap.
        batch_size: Embedding batch size (model-specific).
        session: Optional DB session for progress updates.
        doc_model: Optional DocumentModel for progress updates.
        **chunk_kwargs: Extra params for chunking strategy (e.g. separator).

    Returns:
        IngestionResult with processed nodes and timing trace.
    """
    timings: Dict[str, float] = {}

    # 1. Parse
    _update_progress(session, doc_model, step="parsing", parse_progress=0)
    t0 = time.perf_counter()
    documents = parse_file(file_path, file_type)
    timings["parse_ms"] = round((time.perf_counter() - t0) * 1000, 2)
    _update_progress(session, doc_model, parse_progress=100)

    if not documents:
        TerraLogUtil.warning("ingestion_empty_document", file_path=file_path)
        return IngestionResult(nodes=[], trace=timings)

    # 2. Chunk
    _update_progress(session, doc_model, step="chunking", chunk_progress=0)
    t0 = time.perf_counter()
    nodes = chunk_documents(
        documents,
        method=chunk_method,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        **chunk_kwargs,
    )
    timings["chunk_ms"] = round((time.perf_counter() - t0) * 1000, 2)
    _update_progress(session, doc_model, chunk_progress=100)

    if not nodes:
        TerraLogUtil.warning(
            "ingestion_empty_after_chunking", file_path=file_path)
        return IngestionResult(nodes=[], trace=timings)

    # 3. Inject metadata into every node
    # NOTE: use "source_doc_id" instead of "doc_id" because LlamaIndex
    # PGVectorStore overwrites metadata["doc_id"] with its internal
    # ref_doc_id (a UUID).
    for idx, node in enumerate(nodes):
        node.metadata["source_doc_id"] = doc_id
        node.metadata["kb_id"] = kb_id
        node.metadata["workspace_id"] = workspace_id
        node.metadata["chunk_index"] = idx
        # Exclude filter-only fields from LLM context
        node.excluded_llm_metadata_keys = [
            "source_doc_id", "kb_id", "workspace_id", "chunk_index"]

    # 4. Embed
    _update_progress(session, doc_model, step="embedding", embed_progress=0)
    t0 = time.perf_counter()
    texts = [n.get_content() for n in nodes]
    embeddings = await _batch_embed(
        embed_model, texts, session, doc_model, batch_size=batch_size,
    )
    for node, emb in zip(nodes, embeddings, strict=True):
        node.embedding = emb
    timings["embed_ms"] = round((time.perf_counter() - t0) * 1000, 2)
    _update_progress(session, doc_model, embed_progress=100)

    TerraLogUtil.info(
        "ingestion_pipeline_completed",
        file_path=file_path,
        chunk_count=len(nodes),
        timings=timings,
    )
    return IngestionResult(nodes=nodes, trace=timings)


async def _batch_embed(
    embed_model: BaseEmbedding,
    texts: List[str],
    session: Optional[Session] = None,
    doc_model: Optional[DocumentModel] = None,
    batch_size: int = DEFAULT_SAFE_BATCH_SIZE,
) -> List[List[float]]:
    """Embed texts in batches with adaptive retry on batch-size errors.

    If the embedding API rejects the batch size, automatically halves it
    and retries until it succeeds or batch_size reaches 1.

    Args:
        embed_model: LlamaIndex embedding model.
        texts: Texts to embed.
        session: Optional DB session for progress tracking.
        doc_model: Optional DocumentModel for progress tracking.
        batch_size: Initial batch size.

    Returns:
        List of embedding vectors.
    """
    all_embeddings: List[List[float]] = []
    total = len(texts)
    current_batch_size = batch_size
    start = 0

    while start < total:
        batch = texts[start: start + current_batch_size]
        try:
            batch_embeddings = await embed_model.aget_text_embedding_batch(
                batch)
            all_embeddings.extend(batch_embeddings)
            start += len(batch)
            # Update embed progress proportionally
            if session and doc_model and total > 0:
                progress = min(99, int(start / total * 100))
                _update_progress(session, doc_model, embed_progress=progress)
        except Exception as exc:
            error_msg = str(exc).lower()
            if "batch" in error_msg and current_batch_size > 1:
                new_size = max(1, current_batch_size // 2)
                TerraLogUtil.warning(
                    "embedding_batch_size_reduced",
                    old_size=current_batch_size,
                    new_size=new_size,
                    error=str(exc),
                )
                current_batch_size = new_size
                # Retry the same batch with smaller size — do not advance start
            else:
                raise

    return all_embeddings
