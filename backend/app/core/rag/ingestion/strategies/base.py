"""Abstract base class for chunking strategies."""

from abc import ABC, abstractmethod
from typing import List

from llama_index.core.schema import BaseNode, Document


class ChunkingStrategy(ABC):
    """Base class that all chunking strategies must implement."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique strategy identifier (e.g. 'naive', 'sentence')."""

    @abstractmethod
    def chunk(
        self,
        documents: List[Document],
        chunk_size: int,
        chunk_overlap: int,
        **kwargs,
    ) -> List[BaseNode]:
        """Split documents into nodes.

        Args:
            documents: LlamaIndex Document objects.
            chunk_size: Target chunk size in characters/tokens.
            chunk_overlap: Overlap between consecutive chunks.
            **kwargs: Strategy-specific parameters (e.g. separator).

        Returns:
            List of LlamaIndex BaseNode objects.
        """
