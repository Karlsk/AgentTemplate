"""Amazon Redshift database connector (PostgreSQL-compatible)."""

import time
from typing import List
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text as sa_text

from app.core.common.logging import TerraLogUtil
from app.core.nl2sql.connector.base import DatabaseConnector
from app.schemas.nl2sql import DbConfigTestResponse


class RedshiftConnector(DatabaseConnector):
    """Connector for Amazon Redshift databases (PostgreSQL-compatible)."""

    @property
    def db_type(self) -> str:
        return "redshift"

    @property
    def default_port(self) -> int:
        return 5439

    def build_connection_url(self, host: str, port: int, database: str,
                             username: str, password: str,
                             schema: str = "", extra_params: str = "",
                             ) -> str:
        user = quote_plus(username)
        pwd = quote_plus(password)
        url = f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{database}"
        if extra_params:
            url += f"?{extra_params}"
        return url

    def _effective_schema(self, schema: str) -> str:
        return schema or "public"

    def test_connection(self, host: str, port: int, database: str,
                        username: str, password: str,
                        schema: str = "", extra_params: str = "",
                        ) -> DbConfigTestResponse:
        url = self.build_connection_url(
            host, port, database, username, password, schema, extra_params)
        try:
            engine = create_engine(url, connect_args={"connect_timeout": 10})
            t0 = time.perf_counter()
            with engine.connect() as conn:
                conn.execute(sa_text("SELECT 1"))
            latency = round((time.perf_counter() - t0) * 1000, 2)
            engine.dispose()
            return DbConfigTestResponse(
                success=True, message="Connection successful", latency_ms=latency)
        except Exception as exc:
            TerraLogUtil.warning(
                "redshift_connection_test_failed", error=str(exc))
            return DbConfigTestResponse(
                success=False, message=str(exc), latency_ms=None)

    def get_tables(self, host: str, port: int, database: str,
                   username: str, password: str,
                   schema: str = "", extra_params: str = "",
                   ) -> List[dict]:
        url = self.build_connection_url(
            host, port, database, username, password, schema, extra_params)
        ns = self._effective_schema(schema)
        engine = create_engine(url)
        try:
            with engine.connect() as conn:
                rows = conn.execute(sa_text(
                    "SELECT t.TABLE_NAME, "
                    "COALESCE(d.description, '') AS table_comment "
                    "FROM information_schema.TABLES t "
                    "LEFT JOIN pg_class c ON c.relname = t.TABLE_NAME "
                    "LEFT JOIN pg_namespace n ON n.oid = c.relnamespace "
                    "  AND n.nspname = t.TABLE_SCHEMA "
                    "LEFT JOIN pg_description d ON d.objoid = c.oid AND d.objsubid = 0 "
                    "WHERE t.TABLE_SCHEMA = :schema "
                    "AND t.TABLE_TYPE = 'BASE TABLE' "
                    "ORDER BY t.TABLE_NAME"
                ), {"schema": ns}).fetchall()
            return [{"table_name": r[0], "table_comment": r[1] or ""}
                    for r in rows]
        finally:
            engine.dispose()

    def get_columns(self, host: str, port: int, database: str,
                    username: str, password: str,
                    table_name: str,
                    schema: str = "", extra_params: str = "",
                    ) -> List[dict]:
        url = self.build_connection_url(
            host, port, database, username, password, schema, extra_params)
        ns = self._effective_schema(schema)
        engine = create_engine(url)
        try:
            with engine.connect() as conn:
                rows = conn.execute(sa_text(
                    "SELECT c.COLUMN_NAME, c.DATA_TYPE, "
                    "COALESCE(d.description, '') AS column_comment, "
                    "CASE WHEN kcu.COLUMN_NAME IS NOT NULL THEN 1 ELSE 0 END AS is_pk, "
                    "CASE WHEN c.IS_NULLABLE = 'YES' THEN 1 ELSE 0 END AS is_nullable "
                    "FROM information_schema.COLUMNS c "
                    "LEFT JOIN pg_class pc ON pc.relname = c.TABLE_NAME "
                    "LEFT JOIN pg_namespace pn ON pn.oid = pc.relnamespace "
                    "  AND pn.nspname = c.TABLE_SCHEMA "
                    "LEFT JOIN pg_attribute pa ON pa.attrelid = pc.oid "
                    "  AND pa.attname = c.COLUMN_NAME "
                    "LEFT JOIN pg_description d ON d.objoid = pc.oid "
                    "  AND d.objsubid = pa.attnum "
                    "LEFT JOIN information_schema.TABLE_CONSTRAINTS tc "
                    "  ON tc.TABLE_SCHEMA = c.TABLE_SCHEMA AND tc.TABLE_NAME = c.TABLE_NAME "
                    "  AND tc.CONSTRAINT_TYPE = 'PRIMARY KEY' "
                    "LEFT JOIN information_schema.KEY_COLUMN_USAGE kcu "
                    "  ON kcu.CONSTRAINT_NAME = tc.CONSTRAINT_NAME "
                    "  AND kcu.TABLE_SCHEMA = tc.TABLE_SCHEMA "
                    "  AND kcu.COLUMN_NAME = c.COLUMN_NAME "
                    "WHERE c.TABLE_SCHEMA = :schema AND c.TABLE_NAME = :table "
                    "ORDER BY c.ORDINAL_POSITION"
                ), {"schema": ns, "table": table_name}).fetchall()
            return [{
                "column_name": r[0],
                "column_type": r[1] or "",
                "column_comment": r[2] or "",
                "is_primary_key": bool(r[3]),
                "is_nullable": bool(r[4]),
            } for r in rows]
        finally:
            engine.dispose()
