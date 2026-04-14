import os
import time
from abc import ABC, abstractmethod
from typing import List, Optional, Any, Dict

from langchain_core.embeddings import Embeddings
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_openai import OpenAIEmbeddings
from pydantic import BaseModel, Field
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.core.common.logging import TerraLogUtil as logger

os.environ["TOKENIZERS_PARALLELISM"] = "false"


class EmbeddingConfig(BaseModel):
    """Embedding model configuration."""
    model_name: str
    dimensions: int
    batch_size: int = 32
    max_seq_len: int = 512
    device: str = "cpu"
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    additional_params: Dict[str, Any] = Field(default_factory=dict)


class BaseEmbedding(Embeddings):
    """Abstract base class for embedding models."""

    def __init__(self, config: EmbeddingConfig):
        self.config = config

    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents."""
        pass

    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        """Embed a single query."""
        pass

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(Exception),
    )
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Unified embedding interface with batching and retries."""
        if not texts:
            return []

        all_embeddings = []
        batch_size = self.config.batch_size

        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i : i + batch_size]
            try:
                t0 = time.monotonic()
                batch_embeddings = self.embed_documents(batch_texts)
                elapsed = time.monotonic() - t0
                logger.debug(
                    "embedded_batch",
                    count=len(batch_texts),
                    elapsed_s=elapsed,
                    model=self.config.model_name,
                )
                all_embeddings.extend(batch_embeddings)
            except Exception:
                logger.exception("embedding_batch_failed", model=self.config.model_name)
                raise

        return all_embeddings


class HuggingFaceEmbedding(BaseEmbedding):
    """Local open-source embedding implementation (BGE, text2vec)."""

    def __init__(self, config: EmbeddingConfig):
        super().__init__(config)
        self._model = HuggingFaceEmbeddings(
            model_name=config.model_name,
            model_kwargs={"device": config.device},
            encode_kwargs={"normalize_embeddings": True},
            cache_folder=config.additional_params.get("cache_folder"),
        )

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._model.embed_documents(texts)

    def embed_query(self, text: str) -> List[float]:
        return self._model.embed_query(text)


class OpenAIEmbedding(BaseEmbedding):
    """Cloud-based OpenAI embedding implementation."""

    def __init__(self, config: EmbeddingConfig):
        super().__init__(config)
        self._model = OpenAIEmbeddings(
            model=config.model_name,
            openai_api_key=config.api_key,
            openai_api_base=config.api_base,
            **config.additional_params,
        )

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._model.embed_documents(texts)

    def embed_query(self, text: str) -> List[float]:
        return self._model.embed_query(text)


class EmbeddingFactory:
    """Factory for creating and hot-reloading embedding models."""

    _instances: Dict[str, BaseEmbedding] = {}

    @classmethod
    def get_embedding(cls, config: EmbeddingConfig) -> BaseEmbedding:
        """Get or create an embedding instance based on config."""
        # Use model_name and dimensions as cache key
        cache_key = f"{config.model_name}_{config.dimensions}_{config.device}"

        if cache_key not in cls._instances:
            logger.info("loading_embedding_model", model=config.model_name)
            if config.api_key or config.api_base:
                cls._instances[cache_key] = OpenAIEmbedding(config)
            else:
                cls._instances[cache_key] = HuggingFaceEmbedding(config)

        return cls._instances[cache_key]

    @classmethod
    def clear_cache(cls):
        """Clear cached instances for hot-reloading."""
        cls._instances.clear()
        logger.info("embedding_cache_cleared")
