from __future__ import annotations

from typing import Any

from app.core.common.config import settings
from app.core.common.logging import TerraLogUtil as logger
from app.core.rag.store.base import BaseVectorStore
from app.core.rag.store.milvus import MilvusVectorStore
from app.core.rag.store.pgvector import PgVectorStore


def get_vector_store(store_type: str | None = None, **kwargs: Any) -> BaseVectorStore:
    selected = (store_type or settings.RAG_VECTOR_STORE or "pgvector").lower()
    if selected == "milvus":
        logger.info("rag_vector_store_selected", store_type="milvus")
        return MilvusVectorStore(**kwargs)
    logger.info("rag_vector_store_selected", store_type="pgvector")
    return PgVectorStore(**kwargs)

