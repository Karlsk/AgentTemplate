"""Document parser registry."""

from typing import Dict, Set

from app.core.rag.ingestion.parsers.base import ParserStrategy


_registry: Dict[str, ParserStrategy] = {}
_ext_mapping: Dict[str, str] = {}


def register(parser: ParserStrategy) -> None:
    """Register a parser instance by its name and map its extensions."""
    _registry[parser.name] = parser
    for ext in parser.supported_extensions:
        _ext_mapping[ext.lower()] = parser.name


def get(name: str) -> ParserStrategy:
    """Get a registered parser by name.

    Args:
        name: Parser identifier.

    Returns:
        The corresponding ParserStrategy instance.

    Raises:
        ValueError: If the parser name is not registered.
    """
    name = name.lower()
    if name not in _registry:
        available = ", ".join(sorted(_registry.keys()))
        raise ValueError(
            f"Unknown parser '{name}'. Available: {available}")
    return _registry[name]


def get_by_ext(ext: str) -> ParserStrategy:
    """Get a registered parser by file extension.

    Args:
        ext: File extension (lowercase, no dot).

    Returns:
        The corresponding ParserStrategy instance.

    Raises:
        ValueError: If no parser is registered for the extension.
    """
    ext = ext.lower()
    if ext not in _ext_mapping:
        available = ", ".join(sorted(_ext_mapping.keys()))
        raise ValueError(
            f"No parser registered for extension '{ext}'. "
            f"Supported: {available}")
    return _registry[_ext_mapping[ext]]


def available_parsers() -> list[str]:
    """Return a sorted list of registered parser names."""
    return sorted(_registry.keys())


def supported_extensions() -> Set[str]:
    """Return the set of all registered file extensions."""
    return set(_ext_mapping.keys())


def register_ext(ext: str, parser_name: str) -> None:
    """Manually bind an extension to a specific parser.

    Useful for overriding the default mapping (e.g. use a
    custom PDF parser instead of the built-in one).

    Args:
        ext: File extension (lowercase, no dot).
        parser_name: Name of the target parser.

    Raises:
        ValueError: If the parser name is not registered.
    """
    if parser_name not in _registry:
        raise ValueError(f"Parser '{parser_name}' is not registered")
    _ext_mapping[ext.lower()] = parser_name
