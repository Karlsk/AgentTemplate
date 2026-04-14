from __future__ import annotations

from pathlib import Path

from app.core.rag.loader.base import BaseLoader
from app.core.rag.loader.csv_excel import CSVLoader, ExcelLoader
from app.core.rag.loader.docx import DocxLoader
from app.core.rag.loader.html import HTMLLoader
from app.core.rag.loader.markdown import MarkdownLoader
from app.core.rag.loader.pdf import PDFLoader
from app.core.rag.loader.txt import TxtLoader

__all__ = [
    "BaseLoader",
    "TxtLoader",
    "PDFLoader",
    "DocxLoader",
    "MarkdownLoader",
    "HTMLLoader",
    "CSVLoader",
    "ExcelLoader",
    "get_loader",
]

_LOADER_MAP: dict[str, type[BaseLoader]] = {}


def _register_loaders() -> None:
    for cls in (TxtLoader, PDFLoader, DocxLoader, MarkdownLoader, HTMLLoader, CSVLoader, ExcelLoader):
        for ext in cls.supported_extensions:
            _LOADER_MAP[ext.lower()] = cls


_register_loaders()


def get_loader(filename: str) -> BaseLoader:
    """Return an appropriate loader instance based on file extension."""
    ext = Path(filename).suffix.lower()
    loader_cls = _LOADER_MAP.get(ext)
    if loader_cls is None:
        raise ValueError(f"Unsupported file extension: {ext}. Supported: {sorted(_LOADER_MAP.keys())}")
    return loader_cls()
