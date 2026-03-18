"""NL2SQL vector store management using direct pgvector SQL.

Unlike the generic RAG vector store (LlamaIndex PGVectorStore singleton),
NL2SQL uses per-instance dynamic tables for three vector types:
- DDL vectors (schema/table descriptions)
- SQL vectors (question-SQL pairs)
- DOC vectors (documentation/glossary)

This module provides:
- Dynamic table creation/deletion per NL2SQL instance
- Add/delete vectors with associated training_data_id
- Similarity search for each vector type
"""

from typing import List, Optional, Tuple
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text as sa_text
from sqlalchemy.engine import Engine

from app.core.common.config import settings
from app.core.common.logging import TerraLogUtil


# Vector type suffixes for table naming
VECTOR_TYPE_DDL = "ddl"
VECTOR_TYPE_SQL = "sql"
VECTOR_TYPE_DOC = "doc"

_ALL_VECTOR_TYPES = (VECTOR_TYPE_DDL, VECTOR_TYPE_SQL, VECTOR_TYPE_DOC)


def _build_db_url() -> str:
    """Build PostgreSQL connection URL with encoded credentials."""
    user = quote_plus(settings.POSTGRES_USER)
    password = quote_plus(settings.POSTGRES_PASSWORD)
    return (
        f"postgresql+psycopg2://{user}:{password}"
        f"@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    )


def _get_engine() -> Engine:
    """Get a SQLAlchemy engine for vector operations."""
    return create_engine(_build_db_url(), pool_pre_ping=True)


def _table_name(instance_id: int, vector_type: str) -> str:
    """Generate table name for a specific instance and vector type.

    Pattern: nl2sql_vec_{instance_id}_{type}
    Example: nl2sql_vec_42_ddl, nl2sql_vec_42_sql, nl2sql_vec_42_doc
    """
    return f"nl2sql_vec_{instance_id}_{vector_type}"


def _table_exists(engine: Engine, table_name: str) -> bool:
    """Check if a table exists in the database."""
    with engine.connect() as conn:
        result = conn.execute(
            sa_text(
                "SELECT EXISTS ("
                "  SELECT 1 FROM information_schema.tables"
                "  WHERE table_schema = 'public' AND table_name = :table_name"
                ")"
            ),
            {"table_name": table_name},
        ).scalar()
        return bool(result)


def create_instance_tables(instance_id: int, embed_dim: int) -> None:
    """Create all vector tables for a new NL2SQL instance.

    Creates three tables (ddl, sql, doc) with pgvector extension.

    Args:
        instance_id: NL2SQL instance ID.
        embed_dim: Embedding dimension for the vector column.
    """
    engine = _get_engine()

    # Ensure pgvector extension exists
    with engine.connect() as conn:
        conn.execute(sa_text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()

    for vtype in _ALL_VECTOR_TYPES:
        table = _table_name(instance_id, vtype)

        if _table_exists(engine, table):
            TerraLogUtil.info(
                "nl2sql_vector_table_exists",
                instance_id=instance_id,
                vector_type=vtype,
                table=table,
            )
            continue

        # Create table with pgvector column
        # training_data_id links back to nl2sql_training_data.id
        create_sql = sa_text(f"""
            CREATE TABLE {table} (
                id SERIAL PRIMARY KEY,
                training_data_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                embedding vector({embed_dim}),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create index for vector similarity search (IVFFlat or HNSW)
        # Using HNSW for better recall
        index_sql = sa_text(f"""
            CREATE INDEX IF NOT EXISTS idx_{table}_embedding
            ON {table} USING hnsw (embedding vector_cosine_ops)
        """)

        # Index on training_data_id for deletion
        td_index_sql = sa_text(f"""
            CREATE INDEX IF NOT EXISTS idx_{table}_training_data_id
            ON {table} (training_data_id)
        """)

        with engine.connect() as conn:
            conn.execute(create_sql)
            conn.execute(index_sql)
            conn.execute(td_index_sql)
            conn.commit()

        TerraLogUtil.info(
            "nl2sql_vector_table_created",
            instance_id=instance_id,
            vector_type=vtype,
            table=table,
            embed_dim=embed_dim,
        )


def drop_instance_tables(instance_id: int) -> None:
    """Drop all vector tables for an NL2SQL instance.

    Called when deleting an NL2SQL instance.

    Args:
        instance_id: NL2SQL instance ID.
    """
    engine = _get_engine()

    for vtype in _ALL_VECTOR_TYPES:
        table = _table_name(instance_id, vtype)

        if not _table_exists(engine, table):
            continue

        with engine.connect() as conn:
            conn.execute(sa_text(f"DROP TABLE IF EXISTS {table}"))
            conn.commit()

        TerraLogUtil.info(
            "nl2sql_vector_table_dropped",
            instance_id=instance_id,
            vector_type=vtype,
            table=table,
        )


def add_vector(
    instance_id: int,
    vector_type: str,
    training_data_id: int,
    content: str,
    embedding: List[float],
) -> int:
    """Add a single vector to the appropriate table.

    Args:
        instance_id: NL2SQL instance ID.
        vector_type: One of 'ddl', 'sql', 'doc'.
        training_data_id: FK to nl2sql_training_data.id.
        content: Text content for reference.
        embedding: Vector embedding.

    Returns:
        Inserted row ID.
    """
    table = _table_name(instance_id, vector_type)
    engine = _get_engine()

    # Convert embedding list to pgvector format
    embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"

    with engine.connect() as conn:
        result = conn.execute(
            sa_text(f"""
                INSERT INTO {table} (training_data_id, content, embedding)
                VALUES (:td_id, :content, CAST(:embedding AS vector))
                RETURNING id
            """),
            {
                "td_id": training_data_id,
                "content": content,
                "embedding": embedding_str,
            },
        )
        row_id = result.scalar()
        conn.commit()

    TerraLogUtil.info(
        "nl2sql_vector_added",
        instance_id=instance_id,
        vector_type=vector_type,
        training_data_id=training_data_id,
        row_id=row_id,
    )
    return row_id


def add_vectors_batch(
    instance_id: int,
    vector_type: str,
    items: List[Tuple[int, str, List[float]]],
) -> List[int]:
    """Add multiple vectors in a batch.

    Args:
        instance_id: NL2SQL instance ID.
        vector_type: One of 'ddl', 'sql', 'doc'.
        items: List of (training_data_id, content, embedding) tuples.

    Returns:
        List of inserted row IDs.
    """
    if not items:
        return []

    table = _table_name(instance_id, vector_type)
    engine = _get_engine()

    row_ids = []
    with engine.connect() as conn:
        for td_id, content, embedding in items:
            embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"
            result = conn.execute(
                sa_text(f"""
                    INSERT INTO {table} (training_data_id, content, embedding)
                    VALUES (:td_id, :content, CAST(:embedding AS vector))
                    RETURNING id
                """),
                {
                    "td_id": td_id,
                    "content": content,
                    "embedding": embedding_str,
                },
            )
            row_ids.append(result.scalar())
        conn.commit()

    TerraLogUtil.info(
        "nl2sql_vectors_batch_added",
        instance_id=instance_id,
        vector_type=vector_type,
        count=len(row_ids),
    )
    return row_ids


def delete_vector_by_training_data_id(
    instance_id: int,
    vector_type: str,
    training_data_id: int,
) -> int:
    """Delete vector(s) by training_data_id.

    Args:
        instance_id: NL2SQL instance ID.
        vector_type: One of 'ddl', 'sql', 'doc'.
        training_data_id: FK to nl2sql_training_data.id.

    Returns:
        Number of rows deleted.
    """
    table = _table_name(instance_id, vector_type)
    engine = _get_engine()

    if not _table_exists(engine, table):
        return 0

    with engine.connect() as conn:
        result = conn.execute(
            sa_text(f"DELETE FROM {table} WHERE training_data_id = :td_id"),
            {"td_id": training_data_id},
        )
        deleted = result.rowcount
        conn.commit()

    TerraLogUtil.info(
        "nl2sql_vector_deleted",
        instance_id=instance_id,
        vector_type=vector_type,
        training_data_id=training_data_id,
        deleted=deleted,
    )
    return deleted


def delete_vectors_batch(
    instance_id: int,
    vector_type: str,
    training_data_ids: List[int],
) -> int:
    """Delete multiple vectors by training_data_ids.

    Args:
        instance_id: NL2SQL instance ID.
        vector_type: One of 'ddl', 'sql', 'doc'.
        training_data_ids: List of training_data_ids to delete.

    Returns:
        Total number of rows deleted.
    """
    if not training_data_ids:
        return 0

    table = _table_name(instance_id, vector_type)
    engine = _get_engine()

    if not _table_exists(engine, table):
        return 0

    with engine.connect() as conn:
        result = conn.execute(
            sa_text(
                f"DELETE FROM {table} WHERE training_data_id = ANY(:td_ids)"
            ),
            {"td_ids": training_data_ids},
        )
        deleted = result.rowcount
        conn.commit()

    TerraLogUtil.info(
        "nl2sql_vectors_batch_deleted",
        instance_id=instance_id,
        vector_type=vector_type,
        deleted=deleted,
    )
    return deleted


def search_similar(
    instance_id: int,
    vector_type: str,
    query_embedding: List[float],
    top_k: int = 5,
    threshold: Optional[float] = None,
) -> List[Tuple[int, str, float]]:
    """Search for similar vectors using cosine similarity.

    Args:
        instance_id: NL2SQL instance ID.
        vector_type: One of 'ddl', 'sql', 'doc'.
        query_embedding: Query vector.
        top_k: Number of results to return.
        threshold: Optional minimum similarity threshold (0-1).
                   Defaults to settings.NL2SQL_SIMILARITY_THRESHOLD.

    Returns:
        List of (training_data_id, content, similarity_score) tuples,
        sorted by similarity descending.
    """
    table = _table_name(instance_id, vector_type)
    engine = _get_engine()

    if not _table_exists(engine, table):
        TerraLogUtil.warning(
            "nl2sql_search_table_not_exists",
            instance_id=instance_id,
            vector_type=vector_type,
        )
        return []

    threshold = threshold or settings.NL2SQL_SIMILARITY_THRESHOLD

    # Convert embedding to pgvector format
    embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

    # Cosine similarity: 1 - cosine_distance
    # pgvector <=> operator is cosine distance, so similarity = 1 - distance
    query_sql = sa_text(f"""
        SELECT
            training_data_id,
            content,
            1 - (embedding <=> CAST(:query AS vector)) AS similarity
        FROM {table}
        WHERE 1 - (embedding <=> CAST(:query AS vector)) >= :threshold
        ORDER BY similarity DESC
        LIMIT :top_k
    """)

    with engine.connect() as conn:
        rows = conn.execute(
            query_sql,
            {
                "query": embedding_str,
                "threshold": threshold,
                "top_k": top_k,
            },
        ).fetchall()

    results = [(row[0], row[1], float(row[2])) for row in rows]

    TerraLogUtil.info(
        "nl2sql_search_completed",
        instance_id=instance_id,
        vector_type=vector_type,
        top_k=top_k,
        results=len(results),
    )
    return results


def get_vector_count(instance_id: int, vector_type: str) -> int:
    """Get the count of vectors in a table.

    Args:
        instance_id: NL2SQL instance ID.
        vector_type: One of 'ddl', 'sql', 'doc'.

    Returns:
        Number of vectors in the table.
    """
    table = _table_name(instance_id, vector_type)
    engine = _get_engine()

    if not _table_exists(engine, table):
        return 0

    with engine.connect() as conn:
        count = conn.execute(
            sa_text(f"SELECT COUNT(*) FROM {table}")
        ).scalar()

    return count or 0


def instance_tables_exist(instance_id: int) -> bool:
    """Check if all vector tables exist for an instance.

    Args:
        instance_id: NL2SQL instance ID.

    Returns:
        True if all three tables exist, False otherwise.
    """
    engine = _get_engine()
    for vtype in _ALL_VECTOR_TYPES:
        if not _table_exists(engine, _table_name(instance_id, vtype)):
            return False
    return True
