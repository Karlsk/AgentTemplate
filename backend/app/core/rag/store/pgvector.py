from __future__ import annotations

import json
import re
import time
from typing import Any

from sqlalchemy import text
from sqlmodel import Session

from app.core.common.logging import TerraLogUtil as logger
from app.core.common.db import engine
from app.core.rag.models.document import Chunk, Metadata
from app.core.rag.models.search import ScoredDocument
from app.core.rag.store.base import BaseVectorStore


class PgVectorStore(BaseVectorStore):
    """PostgreSQL + pgvector implementation of vector store."""

    def __init__(self, settings: Any | None = None):
        self._engine = engine
        self._ensure_pgvector_extension()

    def _ensure_pgvector_extension(self):
        """Ensure pgvector extension is created in the database."""
        with Session(self._engine) as session:
            try:
                session.exec(text("CREATE EXTENSION IF NOT EXISTS vector"))
                session.commit()
            except Exception as e:
                logger.exception("pgvector_extension_create_failed")
                session.rollback()

    def _get_table_name(self, collection: str) -> str:
        """Sanitize collection name to be a valid PostgreSQL table name."""
        safe = re.sub(r"[^a-zA-Z0-9_]", "_", collection)
        if not safe:
            safe = "default"
        if safe[0].isdigit():
            safe = f"c_{safe}"
        return f"rag_{safe.lower()}"

    def create_collection(self, name: str, dimension: int, **kwargs: Any) -> None:
        table_name = self._get_table_name(name)

        with Session(self._engine) as session:
            check_sql = text(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = :table_name
                )
                """
            )
            result = session.exec(check_sql, params={"table_name": table_name}).first()

            if result and result[0]:
                logger.info("rag_collection_already_exists", collection=name, table_name=table_name)
                return

            create_sql = text(
                f"""
                CREATE TABLE {table_name} (
                    id VARCHAR(64) PRIMARY KEY,
                    content TEXT,
                    document_id VARCHAR(64),
                    metadata_json JSONB,
                    embedding vector({dimension})
                )
                """
            )
            session.exec(create_sql)

            try:
                index_sql = text(
                    f"""
                    CREATE INDEX {table_name}_embedding_idx ON {table_name}
                    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)
                    """
                )
                session.exec(index_sql)
            except Exception:
                logger.exception("rag_pgvector_index_create_failed", table_name=table_name)
            
            session.commit()
            logger.info(
                "rag_collection_created",
                collection=name,
                table_name=table_name,
                dimension=dimension,
            )

    def drop_collection(self, name: str) -> None:
        table_name = self._get_table_name(name)
        with Session(self._engine) as session:
            try:
                session.exec(text(f"DROP TABLE IF EXISTS {table_name}"))
                session.commit()
                logger.info("rag_collection_dropped", collection=name, table_name=table_name)
            except Exception as e:
                session.rollback()
                logger.exception("rag_collection_drop_failed", collection=name, table_name=table_name)

    def has_collection(self, name: str) -> bool:
        table_name = self._get_table_name(name)
        with Session(self._engine) as session:
            check_sql = text(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = :table_name
                )
                """
            )
            result = session.exec(check_sql, params={"table_name": table_name}).first()
            return bool(result and result[0])

    def insert(self, collection: str, chunks: list[Chunk]) -> list[str]:
        if not chunks:
            return []

        table_name = self._get_table_name(collection)
        t0 = time.monotonic()
        inserted_ids = []

        with Session(self._engine) as session:
            insert_sql = text(
                f"""
                INSERT INTO {table_name} (id, content, document_id, metadata_json, embedding)
                VALUES (:id, :content, :document_id, (:metadata_json)::jsonb, (:embedding)::vector)
                ON CONFLICT (id) DO UPDATE SET
                    content = EXCLUDED.content,
                    document_id = EXCLUDED.document_id,
                    metadata_json = EXCLUDED.metadata_json,
                    embedding = EXCLUDED.embedding
                """
            )

            for chunk in chunks:
                if chunk.embedding is None:
                    continue

                session.exec(
                    insert_sql,
                    params={
                        "id": chunk.id,
                        "content": chunk.content,
                        "document_id": chunk.document_id,
                        "metadata_json": json.dumps(chunk.metadata.model_dump()),
                        "embedding": f"[{','.join(map(str, chunk.embedding))}]"
                    }
                )
                inserted_ids.append(chunk.id)
            
            session.commit()

        elapsed = time.monotonic() - t0
        logger.info("rag_chunks_inserted", collection=collection, count=len(inserted_ids), elapsed_s=elapsed)
        return inserted_ids

    def search(
        self,
        collection: str,
        query_vector: list[float],
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[ScoredDocument]:
        table_name = self._get_table_name(collection)
        t0 = time.monotonic()

        filter_clause = ""
        filter_params = {}

        if filters:
            conditions = []
            for k, v in filters.items():
                param_name = f"filter_{k}"
                if isinstance(v, str):
                    conditions.append(f"metadata_json->>'{k}' = :{param_name}")
                else:
                    conditions.append(f"(metadata_json->>'{k}')::numeric = :{param_name}")
                filter_params[param_name] = v

            if conditions:
                filter_clause = "WHERE " + " AND ".join(conditions)

        vector_str = f"[{','.join(map(str, query_vector))}]"

        with Session(self._engine) as session:
            search_sql = text(
                f"""
                SELECT id, content, document_id, metadata_json, 
                       embedding <=> (:query_vector)::vector AS distance
                FROM {table_name}
                {filter_clause}
                ORDER BY distance ASC
                LIMIT :top_k
                """
            )

            params = {"query_vector": vector_str, "top_k": top_k}
            params.update(filter_params)

            results = session.exec(search_sql, params=params).all()

            scored: list[ScoredDocument] = []
            for row in results:
                id_, content, doc_id, meta_json, distance = row

                similarity = 1.0 - float(distance)

                metadata = Metadata.model_validate(meta_json if isinstance(meta_json, dict) else json.loads(meta_json))

                chunk = Chunk(
                    id=id_,
                    content=content,
                    document_id=doc_id,
                    metadata=metadata,
                )

                scored.append(ScoredDocument(
                    chunk=chunk, 
                    score=similarity,
                    vector_score=similarity,
                ))

        elapsed = time.monotonic() - t0
        logger.info("rag_vector_search_completed", collection=collection, top_k=top_k, results=len(scored), elapsed_s=elapsed)
        return scored

    def delete(self, collection: str, ids: list[str]) -> None:
        if not ids:
            return

        table_name = self._get_table_name(collection)
        with Session(self._engine) as session:
            delete_sql = text(f"DELETE FROM {table_name} WHERE id = ANY(:ids)")
            session.exec(delete_sql, params={"ids": ids})
            session.commit()
            logger.info("rag_chunks_deleted", collection=collection, count=len(ids))

    def count(self, collection: str) -> int:
        table_name = self._get_table_name(collection)
        with Session(self._engine) as session:
            try:
                count_sql = text(f"SELECT COUNT(*) FROM {table_name}")
                result = session.exec(count_sql).first()
                return result[0] if result else 0
            except Exception:
                return 0

    def list_chunks(self, collection: str, limit: int = 10000) -> list[Chunk]:
        table_name = self._get_table_name(collection)
        t0 = time.monotonic()

        with Session(self._engine) as session:
            query_sql = text(
                f"""
                SELECT id, content, document_id, metadata_json 
                FROM {table_name} 
                LIMIT :limit
                """
            )

            results = session.exec(query_sql, params={"limit": limit}).all()

            chunks: list[Chunk] = []
            for row in results:
                id_, content, doc_id, meta_json = row
                metadata = Metadata.model_validate(
                    meta_json if isinstance(meta_json, dict) else json.loads(meta_json)
                )
                chunks.append(Chunk(
                    id=id_,
                    content=content,
                    document_id=doc_id,
                    metadata=metadata,
                ))

        elapsed = time.monotonic() - t0
        logger.info("rag_chunks_listed", collection=collection, count=len(chunks), elapsed_s=elapsed)
        return chunks
