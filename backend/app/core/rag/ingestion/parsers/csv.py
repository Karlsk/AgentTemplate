"""CSV file parser."""

import csv
from typing import List, Set

from llama_index.core.schema import Document

from app.core.rag.ingestion.parsers.base import ParserStrategy


class CsvParser(ParserStrategy):
    """Parse CSV files, treating each row as text."""

    @property
    def name(self) -> str:
        return "csv"

    @property
    def supported_extensions(self) -> Set[str]:
        return {"csv"}

    def parse(self, file_path: str) -> List[Document]:
        rows: List[str] = []
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f)
            for row in reader:
                rows.append(", ".join(row))

        if not rows:
            return []
        text = "\n".join(rows)
        return [Document(text=text, metadata={"source": file_path})]
