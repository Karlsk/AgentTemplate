"""Chunking strategies using LlamaIndex node parsers.

Provides RAGFlow-style chunking methods:
- naive  : fixed-size character splitting (RecursiveCharacterTextSplitter-like)
- sentence: sentence-aware splitting via SentenceSplitter
"""

from enum import Enum
from typing import List, Optional

from llama_index.core.node_parser import (
    SentenceSplitter,
    TokenTextSplitter,
)
from llama_index.core.schema import BaseNode, Document

from app.core.common.config import settings
from app.core.common.logging import TerraLogUtil


class ChunkMethod(str, Enum):
    """Supported chunking methods (aligned with RAGFlow naming)."""

    NAIVE = "naive"
    SENTENCE = "sentence"
    TOKEN = "token"


def chunk_documents(
    documents: List[Document],
    method: str = ChunkMethod.NAIVE,
    chunk_size: int = settings.RAG_DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = settings.RAG_DEFAULT_CHUNK_OVERLAP,
) -> List[BaseNode]:
    """Split documents into nodes using the specified chunking method.

    Args:
        documents: LlamaIndex Document objects.
        method: Chunking strategy name.
        chunk_size: Target chunk size in characters/tokens.
        chunk_overlap: Overlap between consecutive chunks.

    Returns:
        List of LlamaIndex TextNode objects.
    """
    method = method.lower()

    if method == ChunkMethod.TOKEN:
        splitter = TokenTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
    elif method == ChunkMethod.SENTENCE:
        splitter = SentenceSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            paragraph_separator="\n\n",
            secondary_chunking_regex="[。.！!？?；;]",
        )
    else:
        # naive — default, use SentenceSplitter with broad separators
        splitter = SentenceSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    nodes = splitter.get_nodes_from_documents(documents, show_progress=False)

    TerraLogUtil.info(
        "chunking_completed",
        method=method,
        input_docs=len(documents),
        output_nodes=len(nodes),
        chunk_size=chunk_size,
    )
    return nodes
