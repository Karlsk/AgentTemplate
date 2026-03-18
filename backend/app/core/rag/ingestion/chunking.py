"""Chunking entry point — delegates to registered strategies.

Provides RAGFlow-style chunking methods:
- naive     : fixed-size character splitting
- sentence  : sentence-aware splitting (CJK friendly)
- token     : token-count based splitting
- delimiter : custom separator-based splitting
"""

from enum import Enum
from typing import List

from llama_index.core.schema import BaseNode, Document

# Importing the package triggers auto-registration of all built-in strategies
import app.core.rag.ingestion.strategies  # noqa: F401
from app.core.rag.ingestion.strategies import registry
from app.core.common.config import settings
from app.core.common.logging import TerraLogUtil


class ChunkMethod(str, Enum):
    """Supported chunking methods."""

    NAIVE = "naive"
    SENTENCE = "sentence"
    TOKEN = "token"
    DELIMITER = "delimiter"


def chunk_documents(
    documents: List[Document],
    method: str = ChunkMethod.NAIVE,
    chunk_size: int = settings.RAG_DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = settings.RAG_DEFAULT_CHUNK_OVERLAP,
    **kwargs,
) -> List[BaseNode]:
    """Split documents into nodes using the specified chunking strategy.

    Args:
        documents: LlamaIndex Document objects.
        method: Chunking strategy name.
        chunk_size: Target chunk size in characters/tokens.
        chunk_overlap: Overlap between consecutive chunks.
        **kwargs: Strategy-specific params (e.g. separator for delimiter).

    Returns:
        List of LlamaIndex BaseNode objects.
    """
    method = method.lower()
    strategy = registry.get(method)

    nodes = strategy.chunk(
        documents,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        **kwargs,
    )

    TerraLogUtil.info(
        "chunking_completed",
        method=method,
        input_docs=len(documents),
        output_nodes=len(nodes),
        chunk_size=chunk_size,
    )
    return nodes
