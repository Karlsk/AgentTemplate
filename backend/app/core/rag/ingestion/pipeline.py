"""Ingestion pipeline: parse → chunk → embed → store.

Orchestrates the full document ingestion flow using LlamaIndex components.
"""

import time
from typing import Any, Dict, List, Optional

from llama_index.core.embeddings import BaseEmbedding
from llama_index.core.schema import BaseNode, TextNode

from app.core.common.config import settings
from app.core.common.logging import TerraLogUtil
from app.core.rag.ingestion.chunking import ChunkMethod, chunk_documents
from app.core.rag.ingestion.parser import parse_file


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
) -> IngestionResult:
    """Run the full ingestion pipeline on a single file.

    Steps:
        1. Parse file → LlamaIndex Documents
        2. Chunk documents → TextNode list
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

    Returns:
        IngestionResult with processed nodes and timing trace.
    """
    timings: Dict[str, float] = {}

    # 1. Parse
    t0 = time.perf_counter()
    documents = parse_file(file_path, file_type)
    timings["parse_ms"] = round((time.perf_counter() - t0) * 1000, 2)

    if not documents:
        TerraLogUtil.warning("ingestion_empty_document", file_path=file_path)
        return IngestionResult(nodes=[], trace=timings)

    # 2. Chunk
    t0 = time.perf_counter()
    nodes = chunk_documents(
        documents,
        method=chunk_method,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    timings["chunk_ms"] = round((time.perf_counter() - t0) * 1000, 2)

    if not nodes:
        TerraLogUtil.warning(
            "ingestion_empty_after_chunking", file_path=file_path)
        return IngestionResult(nodes=[], trace=timings)

    # 3. Inject metadata into every node
    for idx, node in enumerate(nodes):
        node.metadata["doc_id"] = doc_id
        node.metadata["kb_id"] = kb_id
        node.metadata["workspace_id"] = workspace_id
        node.metadata["chunk_index"] = idx
        # Exclude filter-only fields from LLM context
        node.excluded_llm_metadata_keys = [
            "doc_id", "kb_id", "workspace_id", "chunk_index"]

    # 4. Embed
    t0 = time.perf_counter()
    texts = [n.get_content() for n in nodes]
    embeddings = await _batch_embed(embed_model, texts)
    for node, emb in zip(nodes, embeddings, strict=True):
        node.embedding = emb
    timings["embed_ms"] = round((time.perf_counter() - t0) * 1000, 2)

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
    batch_size: int = settings.RAG_EMBEDDING_BATCH_SIZE,
) -> List[List[float]]:
    """Embed texts in batches.

    Args:
        embed_model: LlamaIndex embedding model.
        texts: Texts to embed.
        batch_size: Batch size.

    Returns:
        List of embedding vectors.
    """
    all_embeddings: List[List[float]] = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start: start + batch_size]
        batch_embeddings = await embed_model.aget_text_embedding_batch(batch)
        all_embeddings.extend(batch_embeddings)
    return all_embeddings
