"""Naive chunking strategy — fixed-size splitting with broad separators."""

from typing import List

from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import BaseNode, Document

from app.core.rag.ingestion.strategies.base import ChunkingStrategy


class NaiveStrategy(ChunkingStrategy):
    """Default fixed-size character splitting using SentenceSplitter."""

    @property
    def name(self) -> str:
        """Strategy identifier."""
        return "naive"

    def chunk(
        self,
        documents: List[Document],
        chunk_size: int,
        chunk_overlap: int,
        **kwargs,
    ) -> List[BaseNode]:
        """Split using SentenceSplitter with default separators."""
        splitter = SentenceSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        return splitter.get_nodes_from_documents(documents, show_progress=False)
