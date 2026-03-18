"""Database connector factory and registry."""

from typing import Dict

from app.core.nl2sql.connector.base import DatabaseConnector


_registry: Dict[str, DatabaseConnector] = {}


def register(connector: DatabaseConnector) -> None:
    """Register a database connector by its db_type."""
    _registry[connector.db_type] = connector


def get(db_type: str) -> DatabaseConnector:
    """Get a registered connector by database type.

    Args:
        db_type: Database type identifier.

    Returns:
        The corresponding DatabaseConnector instance.

    Raises:
        ValueError: If the database type is not registered.
    """
    db_type = db_type.lower()
    if db_type not in _registry:
        available = ", ".join(sorted(_registry.keys()))
        raise ValueError(
            f"Unsupported database type '{db_type}'. Available: {available}")
    return _registry[db_type]


def available_types() -> list[str]:
    """Return a sorted list of supported database types."""
    return sorted(_registry.keys())
