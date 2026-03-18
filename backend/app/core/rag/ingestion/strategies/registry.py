"""Chunking strategy registry."""

from typing import Dict, Type

from app.core.rag.ingestion.strategies.base import ChunkingStrategy


_registry: Dict[str, ChunkingStrategy] = {}


def register(strategy: ChunkingStrategy) -> None:
    """Register a strategy instance by its name."""
    _registry[strategy.name] = strategy


def get(name: str) -> ChunkingStrategy:
    """Get a registered strategy by name.

    Args:
        name: Strategy identifier.

    Returns:
        The corresponding ChunkingStrategy instance.

    Raises:
        ValueError: If the strategy name is not registered.
    """
    name = name.lower()
    if name not in _registry:
        available = ", ".join(sorted(_registry.keys()))
        raise ValueError(
            f"Unknown chunking strategy '{name}'. Available: {available}")
    return _registry[name]


def available_strategies() -> list[str]:
    """Return a sorted list of registered strategy names."""
    return sorted(_registry.keys())
