"""Auto-register all built-in document parsers."""

from app.core.rag.ingestion.parsers import registry
from app.core.rag.ingestion.parsers.csv import CsvParser
from app.core.rag.ingestion.parsers.docx import DocxParser
from app.core.rag.ingestion.parsers.html import HtmlParser
from app.core.rag.ingestion.parsers.markdown import MarkdownParser
from app.core.rag.ingestion.parsers.pdf import PdfParser
from app.core.rag.ingestion.parsers.txt import TxtParser

registry.register(TxtParser())
registry.register(PdfParser())
registry.register(DocxParser())
registry.register(MarkdownParser())
registry.register(HtmlParser())
registry.register(CsvParser())
