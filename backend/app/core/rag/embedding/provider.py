"""LlamaIndex embedding provider abstraction.

Wraps LlamaIndex OpenAIEmbedding to create workspace-aware,
cacheable embedding provider instances from the system's ai_model config.
"""

import threading
from typing import Dict, List

from llama_index.core.embeddings import BaseEmbedding
from llama_index.embeddings.openai import OpenAIEmbedding
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.common.config import settings
from app.core.common.logging import TerraLogUtil


def create_embedding_model(
    model_name: str,
    api_key: str,
    api_base: str,
    dimension: int = 1536,
) -> BaseEmbedding:
    """Create a LlamaIndex embedding model instance.

    Args:
        model_name: Embedding model name (e.g. text-embedding-3-small).
        api_key: API key for the embedding service.
        api_base: Base URL for the API.
        dimension: Embedding vector dimension.

    Returns:
        A LlamaIndex BaseEmbedding instance.
    """
    return OpenAIEmbedding(
        model_name=model_name,
        api_key=api_key,
        api_base=api_base,
        dimensions=dimension,
    )


class EmbeddingProviderRegistry:
    """Thread-safe registry for cached embedding provider instances.

    Caches one provider per ai_model ID to avoid recreating clients.
    """

    _instances: Dict[int, BaseEmbedding] = {}
    _lock = threading.Lock()

    @classmethod
    def get(
        cls,
        model_id: int,
        model_name: str,
        api_key: str,
        api_base: str,
        dimension: int = 1536,
    ) -> BaseEmbedding:
        """Get or create an embedding model by ai_model ID.

        Args:
            model_id: Primary key in the ai_model table.
            model_name: Model name string.
            api_key: API key.
            api_base: API base URL.
            dimension: Embedding dimension.

        Returns:
            Cached or new BaseEmbedding instance.
        """
        with cls._lock:
            if model_id not in cls._instances:
                TerraLogUtil.info(
                    "embedding_provider_created",
                    model_id=model_id,
                    model_name=model_name,
                )
                cls._instances[model_id] = create_embedding_model(
                    model_name=model_name,
                    api_key=api_key,
                    api_base=api_base,
                    dimension=dimension,
                )
            return cls._instances[model_id]

    @classmethod
    def clear(cls) -> None:
        """Clear all cached instances."""
        with cls._lock:
            cls._instances.clear()
