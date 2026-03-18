"""Kingbase (人大金仓) database connector (PostgreSQL-compatible)."""

import time
from typing import List
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text as sa_text

from app.core.common.logging import TerraLogUtil
from app.core.nl2sql.connector.base import DatabaseConnector
from app.schemas.nl2sql import DbConfigTestResponse


class KingbaseConnector(DatabaseConnector):
    """Connector for Kingbase (人大金仓) databases (PostgreSQL-compatible)."""

    @property
    def db_type(self) -> str:
        return "kingbase"

    @property
    def default_port(self) -> int:
        return 54321

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
                "kingbase_connection_test_failed", error=str(exc))
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
                    "SELECT c.relname AS table_name, "
                    "COALESCE(d.description, obj_description(c.oid)) AS table_comment "
                    "FROM pg_class c "
                    "LEFT JOIN pg_namespace n ON n.oid = c.relnamespace "
                    "LEFT JOIN pg_description d ON d.objoid = c.oid AND d.objsubid = 0 "
                    "WHERE n.nspname = :schema AND c.relkind IN ('r', 'v', 'p', 'm') "
                    "ORDER BY c.relname"
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
                    "SELECT a.attname AS column_name, "
                    "pg_catalog.format_type(a.atttypid, a.atttypmod) AS column_type, "
                    "col_description(c.oid, a.attnum) AS column_comment, "
                    "CASE WHEN pk.contype = 'p' THEN true ELSE false END AS is_pk, "
                    "NOT a.attnotnull AS is_nullable "
                    "FROM pg_catalog.pg_attribute a "
                    "JOIN pg_catalog.pg_class c ON c.oid = a.attrelid "
                    "JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace "
                    "LEFT JOIN pg_constraint pk "
                    "  ON pk.conrelid = c.oid AND pk.contype = 'p' "
                    "  AND a.attnum = ANY(pk.conkey) "
                    "WHERE n.nspname = :schema AND c.relname = :table "
                    "AND a.attnum > 0 AND NOT a.attisdropped "
                    "ORDER BY a.attnum"
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
