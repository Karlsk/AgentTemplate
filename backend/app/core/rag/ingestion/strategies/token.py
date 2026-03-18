"""Token-based chunking strategy."""

from typing import List

from llama_index.core.node_parser import TokenTextSplitter
from llama_index.core.schema import BaseNode, Document

from app.core.rag.ingestion.strategies.base import ChunkingStrategy


class TokenStrategy(ChunkingStrategy):
    """Token-count based splitting."""

    @property
    def name(self) -> str:
        """Strategy identifier."""
        return "token"

    def chunk(
        self,
        documents: List[Document],
        chunk_size: int,
        chunk_overlap: int,
        **kwargs,
    ) -> List[BaseNode]:
        """Split by token count."""
        splitter = TokenTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        return splitter.get_nodes_from_documents(documents, show_progress=False)
