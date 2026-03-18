"""Sentence-aware chunking strategy with CJK support."""

from typing import List

from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import BaseNode, Document

from app.core.rag.ingestion.strategies.base import ChunkingStrategy


class SentenceStrategy(ChunkingStrategy):
    """Sentence-aware splitting with CJK punctuation support."""

    @property
    def name(self) -> str:
        """Strategy identifier."""
        return "sentence"

    def chunk(
        self,
        documents: List[Document],
        chunk_size: int,
        chunk_overlap: int,
        **kwargs,
    ) -> List[BaseNode]:
        """Split with sentence-boundary awareness."""
        splitter = SentenceSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            paragraph_separator="\n\n",
            secondary_chunking_regex="[。.！!？?；;]",
        )
        return splitter.get_nodes_from_documents(documents, show_progress=False)
