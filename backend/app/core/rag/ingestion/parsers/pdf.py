"""PDF file parser."""

from typing import List, Set

from pypdf import PdfReader

from llama_index.core.schema import Document

from app.core.rag.ingestion.parsers.base import ParserStrategy


class PdfParser(ParserStrategy):
    """Parse PDF files, one Document per page."""

    @property
    def name(self) -> str:
        return "pdf"

    @property
    def supported_extensions(self) -> Set[str]:
        return {"pdf"}

    def parse(self, file_path: str) -> List[Document]:
        reader = PdfReader(file_path)
        docs: List[Document] = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text and text.strip():
                docs.append(
                    Document(
                        text=text,
                        metadata={"source": file_path, "page": i + 1},
                    )
                )
        return docs
