"""LlamaIndex embedding provider abstraction.

Wraps LlamaIndex OpenAIEmbedding to create workspace-aware,
cacheable embedding provider instances from the system's ai_model config.

Supports dynamic capability detection: probing the model at initialization
to determine the actual embedding dimension, and adaptive batch sizing.
"""

import threading
from dataclasses import dataclass
from typing import Dict, List, Optional

from llama_index.core.embeddings import BaseEmbedding
from llama_index.embeddings.openai import OpenAIEmbedding
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.common.config import settings
from app.core.common.logging import TerraLogUtil

# Safe default batch size that most providers accept
DEFAULT_SAFE_BATCH_SIZE = 8


@dataclass
class EmbeddingModelCapability:
    """Stores dynamically detected capabilities of an embedding model."""

    model: BaseEmbedding
    dimension: int
    batch_size: int


def create_embedding_model(
    model_name: str,
    api_key: str,
    api_base: str,
    dimension: Optional[int] = None,
) -> BaseEmbedding:
    """Create a LlamaIndex embedding model instance.

    Args:
        model_name: Embedding model name (e.g. text-embedding-3-small).
        api_key: API key for the embedding service.
        api_base: Base URL for the API.
        dimension: Embedding vector dimension. If None, do not pass dimensions
                   to the API (let the model use its default).

    Returns:
        A LlamaIndex BaseEmbedding instance.
    """
    kwargs = {
        "model_name": model_name,
        "api_key": api_key,
        "api_base": api_base,
    }
    if dimension is not None:
        kwargs["dimensions"] = dimension
    return OpenAIEmbedding(**kwargs)


async def probe_embedding_dimension(embed_model: BaseEmbedding) -> int:
    """Probe the embedding model to detect its actual output dimension.

    Sends a single short text to the model and measures the returned
    vector length.  This is called once per model at first use.

    Args:
        embed_model: A LlamaIndex BaseEmbedding instance.

    Returns:
        The integer dimension of the embedding vector.

    Raises:
        RuntimeError: If the probe request fails.
    """
    try:
        embedding = await embed_model.aget_text_embedding("dimension probe")
        dim = len(embedding)
        TerraLogUtil.info("embedding_dimension_probed", dimension=dim)
        return dim
    except Exception as exc:
        TerraLogUtil.exception(
            "embedding_dimension_probe_failed", error=str(exc))
        raise RuntimeError(
            f"Failed to probe embedding model dimension: {exc}"
        ) from exc


class EmbeddingProviderRegistry:
    """Thread-safe registry for cached embedding provider instances.

    Caches one provider per ai_model ID to avoid recreating clients.
    Also tracks per-model capabilities (dimension, batch_size).
    """

    _instances: Dict[int, BaseEmbedding] = {}
    _capabilities: Dict[int, EmbeddingModelCapability] = {}
    _lock = threading.Lock()

    @classmethod
    def get(
        cls,
        model_id: int,
        model_name: str,
        api_key: str,
        api_base: str,
        dimension: Optional[int] = None,
    ) -> BaseEmbedding:
        """Get or create an embedding model by ai_model ID.

        Args:
            model_id: Primary key in the ai_model table.
            model_name: Model name string.
            api_key: API key.
            api_base: API base URL.
            dimension: Embedding dimension (None = let model decide).

        Returns:
            Cached or new BaseEmbedding instance.
        """
        with cls._lock:
            if model_id not in cls._instances:
                TerraLogUtil.info(
                    "embedding_provider_created",
                    model_id=model_id,
                    model_name=model_name,
                    dimension=dimension,
                )
                cls._instances[model_id] = create_embedding_model(
                    model_name=model_name,
                    api_key=api_key,
                    api_base=api_base,
                    dimension=dimension,
                )
            return cls._instances[model_id]

    @classmethod
    def set_capability(
        cls,
        model_id: int,
        capability: EmbeddingModelCapability,
    ) -> None:
        """Store detected capability for a model."""
        with cls._lock:
            cls._capabilities[model_id] = capability

    @classmethod
    def get_capability(cls, model_id: int) -> Optional[EmbeddingModelCapability]:
        """Retrieve cached capability for a model."""
        return cls._capabilities.get(model_id)

    @classmethod
    def invalidate(cls, model_id: int) -> None:
        """Remove a specific model from cache (e.g. after config change)."""
        with cls._lock:
            cls._instances.pop(model_id, None)
            cls._capabilities.pop(model_id, None)

    @classmethod
    def clear(cls) -> None:
        """Clear all cached instances and capabilities."""
        with cls._lock:
            cls._instances.clear()
            cls._capabilities.clear()
