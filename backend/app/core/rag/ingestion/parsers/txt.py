"""Plain text file parser."""

from typing import List, Set

from llama_index.core.schema import Document

from app.core.rag.ingestion.parsers.base import ParserStrategy


class TxtParser(ParserStrategy):
    """Parse plain text files."""

    @property
    def name(self) -> str:
        return "txt"

    @property
    def supported_extensions(self) -> Set[str]:
        return {"txt"}

    def parse(self, file_path: str) -> List[Document]:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
        if not text.strip():
            return []
        return [Document(text=text, metadata={"source": file_path})]
