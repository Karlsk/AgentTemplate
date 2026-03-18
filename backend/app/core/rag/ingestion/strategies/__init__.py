"""Chunking strategies package — auto-registers all built-in strategies."""

from app.core.rag.ingestion.strategies import registry
from app.core.rag.ingestion.strategies.delimiter import DelimiterStrategy
from app.core.rag.ingestion.strategies.naive import NaiveStrategy
from app.core.rag.ingestion.strategies.sentence import SentenceStrategy
from app.core.rag.ingestion.strategies.token import TokenStrategy

# Auto-register built-in strategies
registry.register(NaiveStrategy())
registry.register(SentenceStrategy())
registry.register(TokenStrategy())
registry.register(DelimiterStrategy())
