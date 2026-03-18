"""PGVector store wrapper using LlamaIndex PGVectorStore.

Provides helper functions to create, access, and manage the shared
vector store backed by PostgreSQL + pgvector.
"""

import threading
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

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
_store_dimension: Optional[int] = None


def _build_db_url(driver: str = "postgresql") -> str:
    """Build a properly encoded PostgreSQL connection URL.

    Args:
        driver: SQLAlchemy driver prefix (e.g. 'postgresql',
                'postgresql+psycopg2', 'postgresql+asyncpg').
    """
    user = quote_plus(settings.POSTGRES_USER)
    password = quote_plus(settings.POSTGRES_PASSWORD)
    return (
        f"{driver}://{user}:{password}"
        f"@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    )


def _vector_table_exists() -> bool:
    """Check if the LlamaIndex-managed vector table exists in the database."""
    from sqlalchemy import create_engine, text as sa_text

    table = f"data_{settings.RAG_VECTOR_TABLE_NAME}"
    engine = create_engine(_build_db_url())
    try:
        with engine.connect() as conn:
            result = conn.execute(
                sa_text(
                    "SELECT EXISTS ("
                    "  SELECT 1 FROM information_schema.tables"
                    "  WHERE table_schema = 'public' AND table_name = :table_name"
                    ")"
                ),
                {"table_name": table},
            ).scalar()
            return bool(result)
    except Exception:
        return False


def get_vector_store(
    embed_dim: Optional[int] = None,
) -> PGVectorStore:
    """Get or create the singleton PGVectorStore instance.

    LlamaIndex PGVectorStore manages its own table
    (``rag_vectors`` by default) inside the project database.

    When ``embed_dim`` is None and a singleton already exists, the
    existing instance is returned regardless of its dimension. This
    allows callers that don't know the dimension (e.g. retrievers)
    to reuse the store that was created during ingestion.

    Only when a specific ``embed_dim`` is passed **and** it differs
    from the cached dimension will the singleton be recreated.

    Args:
        embed_dim: Embedding dimension. If None, reuse existing or
                   fall back to settings.

    Returns:
        PGVectorStore instance.
    """
    global _store_instance, _store_dimension

    # If a singleton exists and no specific dimension was requested,
    # return it as-is (don't invalidate based on settings default).
    if _store_instance is not None and embed_dim is None:
        return _store_instance

    effective_dim = embed_dim or settings.RAG_EMBEDDING_DIMENSION

    # If a specific dimension was requested and differs, invalidate
    if (
        _store_instance is not None
        and embed_dim is not None
        and _store_dimension != effective_dim
    ):
        TerraLogUtil.info(
            "pgvector_store_dimension_changed",
            old_dim=_store_dimension,
            new_dim=effective_dim,
        )
        with _store_lock:
            _store_instance = None
            _store_dimension = None

    if _store_instance is not None:
        return _store_instance

    with _store_lock:
        if _store_instance is not None:
            return _store_instance

        # Build URL-encoded connection strings to handle special
        # characters (e.g. '@') in passwords correctly.
        conn_str = _build_db_url(driver="postgresql+psycopg2")
        async_conn_str = _build_db_url(driver="postgresql+asyncpg")

        _store_instance = PGVectorStore.from_params(
            connection_string=conn_str,
            async_connection_string=async_conn_str,
            table_name=settings.RAG_VECTOR_TABLE_NAME,
            embed_dim=effective_dim,
        )
        _store_dimension = effective_dim
        TerraLogUtil.info(
            "pgvector_store_initialized",
            table=settings.RAG_VECTOR_TABLE_NAME,
            embed_dim=effective_dim,
        )
        return _store_instance


def add_nodes(
    nodes: List[BaseNode],
    store: Optional[PGVectorStore] = None,
    embed_dim: Optional[int] = None,
) -> List[str]:
    """Insert nodes (with embeddings) into the vector store.

    Args:
        nodes: Nodes produced by the ingestion pipeline.
        store: Optional store override.
        embed_dim: Embedding dimension for vector store initialisation.

    Returns:
        List of inserted node IDs.
    """
    store = store or get_vector_store(embed_dim=embed_dim)
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
    Silently succeeds if the vector table does not exist yet.

    Args:
        key: Metadata key (e.g. "doc_id", "kb_id").
        value: Value to match.
        store: Optional store override.
    """
    if not _vector_table_exists():
        TerraLogUtil.info("pgvector_skip_delete_no_table",
                          key=key, value=value)
        return

    store = store or get_vector_store()

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

    engine = create_engine(_build_db_url())
    table = settings.RAG_VECTOR_TABLE_NAME

    try:
        with engine.connect() as conn:
            conn.execute(
                sa_text(
                    f"DELETE FROM data_{table} WHERE metadata_->>:key = :val"),
                {"key": key, "val": str(value)},
            )
            conn.commit()
        TerraLogUtil.info("pgvector_nodes_deleted_sql", key=key, value=value)
    except Exception:
        TerraLogUtil.warning("pgvector_delete_sql_failed",
                             key=key, value=value)


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


def query_nodes_by_doc_id(
    doc_id: int,
    offset: int = 0,
    limit: int = 20,
) -> tuple[list[dict], int]:
    """Query chunk nodes by source_doc_id for preview, ordered by chunk_index.

    Uses ``source_doc_id`` metadata key (not ``doc_id``) because
    LlamaIndex PGVectorStore overwrites ``doc_id`` with its internal UUID.

    Args:
        doc_id: Document ID to query chunks for.
        offset: Pagination offset.
        limit: Max results to return.

    Returns:
        Tuple of (list of chunk dicts, total count).
    """
    if not _vector_table_exists():
        return [], 0

    from sqlalchemy import create_engine, text as sa_text

    engine = create_engine(_build_db_url())
    table = f"data_{settings.RAG_VECTOR_TABLE_NAME}"

    with engine.connect() as conn:
        count_row = conn.execute(
            sa_text(
                f"SELECT COUNT(*) FROM {table} WHERE metadata_->>'source_doc_id' = :doc_id"),
            {"doc_id": str(doc_id)},
        ).scalar()
        total = count_row or 0

        rows = conn.execute(
            sa_text(
                f"SELECT node_id, text, metadata_ FROM {table} "
                f"WHERE metadata_->>'source_doc_id' = :doc_id "
                f"ORDER BY (metadata_->>'chunk_index')::int "
                f"OFFSET :offset LIMIT :limit"
            ),
            {"doc_id": str(doc_id), "offset": offset, "limit": limit},
        ).fetchall()

    chunks = []
    for row in rows:
        metadata = row[2] if isinstance(row[2], dict) else {}
        chunks.append({
            "chunk_index": metadata.get("chunk_index", 0),
            "content": row[1] or "",
            "char_count": len(row[1] or ""),
            "metadata": {
                k: v for k, v in metadata.items()
                if k not in ("source_doc_id", "kb_id", "workspace_id")
            } or None,
        })

    return chunks, total


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
