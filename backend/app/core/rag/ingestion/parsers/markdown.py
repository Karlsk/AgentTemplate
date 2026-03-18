"""Markdown file parser."""

from typing import List, Set

from llama_index.core.schema import Document

from app.core.rag.ingestion.parsers.base import ParserStrategy


class MarkdownParser(ParserStrategy):
    """Parse Markdown files as plain text."""

    @property
    def name(self) -> str:
        return "markdown"

    @property
    def supported_extensions(self) -> Set[str]:
        return {"md", "markdown"}

    def parse(self, file_path: str) -> List[Document]:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
        if not text.strip():
            return []
        return [Document(text=text, metadata={"source": file_path})]
