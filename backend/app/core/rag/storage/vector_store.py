"""PGVector store wrapper using LlamaIndex PGVectorStore.

Provides helper functions to create, access, and manage the shared
vector store backed by PostgreSQL + pgvector.
"""

import threading
from typing import Any, Dict, List, Optional

from llama_index.core.schema import BaseNode, TextNode
from llama_index.core.vector_stores.types import (
    MetadataFilter,
    MetadataFilters,
    FilterCondition,
    FilterOperator,
    VectorStoreQuery,
    VectorStoreQueryResult,
)
from llama_index.vector_stores.postgres import PGVectorStore

from app.core.common.config import settings
from app.core.common.logging import TerraLogUtil

_store_lock = threading.Lock()
_store_instance: Optional[PGVectorStore] = None


def get_vector_store(
    embed_dim: int = settings.RAG_EMBEDDING_DIMENSION,
) -> PGVectorStore:
    """Get or create the singleton PGVectorStore instance.

    LlamaIndex PGVectorStore manages its own table
    (``rag_vectors`` by default) inside the project database.

    Args:
        embed_dim: Embedding dimension.

    Returns:
        PGVectorStore instance.
    """
    global _store_instance
    if _store_instance is not None:
        return _store_instance

    with _store_lock:
        if _store_instance is not None:
            return _store_instance

        _store_instance = PGVectorStore.from_params(
            database=settings.POSTGRES_DB,
            host=settings.POSTGRES_SERVER,
            port=str(settings.POSTGRES_PORT),
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            table_name=settings.RAG_VECTOR_TABLE_NAME,
            embed_dim=embed_dim,
        )
        TerraLogUtil.info(
            "pgvector_store_initialized",
            table=settings.RAG_VECTOR_TABLE_NAME,
            embed_dim=embed_dim,
        )
        return _store_instance


def add_nodes(nodes: List[BaseNode], store: Optional[PGVectorStore] = None) -> List[str]:
    """Insert nodes (with embeddings) into the vector store.

    Args:
        nodes: Nodes produced by the ingestion pipeline.
        store: Optional store override.

    Returns:
        List of inserted node IDs.
    """
    store = store or get_vector_store()
    ids = store.add(nodes)
    TerraLogUtil.info("pgvector_nodes_added", count=len(ids))
    return ids


def delete_nodes_by_metadata(
    key: str,
    value: Any,
    store: Optional[PGVectorStore] = None,
) -> None:
    """Delete nodes whose metadata[key] == value.

    Useful for deleting all chunks of a document or knowledge base.

    Args:
        key: Metadata key (e.g. "doc_id", "kb_id").
        value: Value to match.
        store: Optional store override.
    """
    store = store or get_vector_store()
    # LlamaIndex PGVectorStore.delete accepts a ref_doc_id or filters
    # Use the low-level delete method with filter
    from sqlalchemy import text as sa_text

    try:
        store.delete_nodes(
            node_ids=None,
            filters=MetadataFilters(
                filters=[
                    MetadataFilter(key=key, value=value,
                                   operator=FilterOperator.EQ),
                ],
            ),
        )
        TerraLogUtil.info("pgvector_nodes_deleted", key=key, value=value)
    except Exception:
        # Fallback: direct SQL delete
        _delete_by_metadata_sql(key, value, store)


def _delete_by_metadata_sql(key: str, value: Any, store: PGVectorStore) -> None:
    """Fallback: delete nodes via raw SQL on the vector table."""
    from sqlalchemy import create_engine, text as sa_text

    db_url = (
        f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    )
    engine = create_engine(db_url)
    table = settings.RAG_VECTOR_TABLE_NAME

    with engine.connect() as conn:
        conn.execute(
            sa_text(f"DELETE FROM data_{table} WHERE metadata_->>:key = :val"),
            {"key": key, "val": str(value)},
        )
        conn.commit()
    TerraLogUtil.info("pgvector_nodes_deleted_sql", key=key, value=value)


def query_vectors(
    query_embedding: List[float],
    top_k: int = 5,
    filters: Optional[MetadataFilters] = None,
) -> VectorStoreQueryResult:
    """Low-level vector similarity query.

    Args:
        query_embedding: Query vector.
        top_k: Number of results.
        filters: Optional metadata filters.

    Returns:
        VectorStoreQueryResult with nodes and similarities.
    """
    store = get_vector_store()
    query = VectorStoreQuery(
        query_embedding=query_embedding,
        similarity_top_k=top_k,
        filters=filters,
    )
    return store.query(query)


def build_kb_filters(
    kb_ids: List[int],
    workspace_id: int,
) -> MetadataFilters:
    """Build LlamaIndex MetadataFilters for workspace/KB scoping.

    Args:
        kb_ids: Knowledge base IDs.
        workspace_id: Workspace ID.

    Returns:
        MetadataFilters for query.
    """
    filters = [
        MetadataFilter(
            key="workspace_id",
            value=workspace_id,
            operator=FilterOperator.EQ,
        ),
    ]
    if len(kb_ids) == 1:
        filters.append(
            MetadataFilter(
                key="kb_id",
                value=kb_ids[0],
                operator=FilterOperator.EQ,
            )
        )
    else:
        filters.append(
            MetadataFilter(
                key="kb_id",
                value=kb_ids,
                operator=FilterOperator.IN,
            )
        )
    return MetadataFilters(filters=filters, condition=FilterCondition.AND)
