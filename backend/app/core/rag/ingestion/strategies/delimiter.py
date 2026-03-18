"""Custom delimiter-based chunking strategy."""

from typing import List

from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import BaseNode, Document

from app.core.rag.ingestion.strategies.base import ChunkingStrategy


class DelimiterStrategy(ChunkingStrategy):
    """Split documents using a user-defined delimiter as the primary separator."""

    @property
    def name(self) -> str:
        """Strategy identifier."""
        return "delimiter"

    def chunk(
        self,
        documents: List[Document],
        chunk_size: int,
        chunk_overlap: int,
        **kwargs,
    ) -> List[BaseNode]:
        """Split using custom delimiter as paragraph separator.

        Args:
            documents: LlamaIndex Documents.
            chunk_size: Max chunk size.
            chunk_overlap: Overlap between chunks.
            **kwargs: Must include 'separator' (str). Falls back to '\\n\\n'.
        """
        separator = kwargs.get("separator", "\n\n")
        splitter = SentenceSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            paragraph_separator=separator,
        )
        return splitter.get_nodes_from_documents(documents, show_progress=False)
