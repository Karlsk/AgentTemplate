import pytest
from sqlalchemy import text
from sqlmodel import Session

from app.core.common.db import engine
from app.core.rag.models.document import Chunk, Metadata
from app.core.rag.store.pgvector import PgVectorStore


def _can_connect() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def _has_pgvector() -> bool:
    try:
        with engine.connect() as conn:
            res = conn.execute(
                text("SELECT 1 FROM pg_extension WHERE extname = 'vector' LIMIT 1")
            ).fetchone()
            return bool(res)
    except Exception:
        return False


@pytest.mark.skipif(not _can_connect(), reason="postgres_not_available")
def test_pgvector_store_roundtrip():
    store = PgVectorStore()
    store._ensure_pgvector_extension()
    if not _has_pgvector():
        pytest.skip("pgvector_extension_not_available")

    collection = "instance_test_pgvector"
    store.create_collection(collection, dimension=3)
    try:
        chunks = [
            Chunk(
                id="c1",
                content="alpha",
                document_id="d1",
                metadata=Metadata(source="unit_test"),
                embedding=[1.0, 0.0, 0.0],
            ),
            Chunk(
                id="c2",
                content="beta",
                document_id="d1",
                metadata=Metadata(source="unit_test"),
                embedding=[0.0, 1.0, 0.0],
            ),
        ]
        store.insert(collection, chunks)
        results = store.search(collection, query_vector=[1.0, 0.0, 0.0], top_k=1)
        assert len(results) == 1
        assert results[0].chunk.id == "c1"
    finally:
        store.drop_collection(collection)

