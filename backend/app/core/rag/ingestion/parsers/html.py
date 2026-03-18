"""HTML file parser."""

from typing import List, Set

from bs4 import BeautifulSoup

from llama_index.core.schema import Document

from app.core.rag.ingestion.parsers.base import ParserStrategy


class HtmlParser(ParserStrategy):
    """Parse HTML files, stripping tags."""

    @property
    def name(self) -> str:
        return "html"

    @property
    def supported_extensions(self) -> Set[str]:
        return {"html", "htm"}

    def parse(self, file_path: str) -> List[Document]:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            html = f.read()

        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)
        if not text.strip():
            return []
        return [Document(text=text, metadata={"source": file_path})]
