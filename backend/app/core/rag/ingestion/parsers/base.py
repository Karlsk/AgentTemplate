"""Abstract base class for document parsers."""

from abc import ABC, abstractmethod
from typing import List, Set

from llama_index.core.schema import Document


class ParserStrategy(ABC):
    """Base class that all document parsers must implement."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique parser identifier (e.g. 'pdf', 'txt')."""

    @property
    @abstractmethod
    def supported_extensions(self) -> Set[str]:
        """File extensions this parser handles (lowercase, no dot)."""

    @abstractmethod
    def parse(self, file_path: str) -> List[Document]:
        """Parse a file into LlamaIndex Document objects.

        Args:
            file_path: Absolute path to the file.

        Returns:
            List of LlamaIndex Document objects.
        """
