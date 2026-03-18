"""Oracle database connector."""

import time
from typing import List
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text as sa_text

from app.core.common.logging import TerraLogUtil
from app.core.nl2sql.connector.base import DatabaseConnector
from app.schemas.nl2sql import DbConfigTestResponse


class OracleConnector(DatabaseConnector):
    """Connector for Oracle databases."""

    @property
    def db_type(self) -> str:
        return "oracle"

    @property
    def default_port(self) -> int:
        return 1521

    def build_connection_url(self, host: str, port: int, database: str,
                             username: str, password: str,
                             schema: str = "", extra_params: str = "",
                             ) -> str:
        user = quote_plus(username)
        pwd = quote_plus(password)
        url = f"oracle+oracledb://{user}:{pwd}@{host}:{port}/?service_name={database}"
        if extra_params:
            url += f"&{extra_params}"
        return url

    def _effective_schema(self, schema: str, username: str) -> str:
        return schema.upper() if schema else username.upper()

    def test_connection(self, host: str, port: int, database: str,
                        username: str, password: str,
                        schema: str = "", extra_params: str = "",
                        ) -> DbConfigTestResponse:
        url = self.build_connection_url(
            host, port, database, username, password, schema, extra_params)
        try:
            engine = create_engine(
                url, connect_args={"tcp_connect_timeout": 10})
            t0 = time.perf_counter()
            with engine.connect() as conn:
                conn.execute(sa_text("SELECT 1 FROM DUAL"))
            latency = round((time.perf_counter() - t0) * 1000, 2)
            engine.dispose()
            return DbConfigTestResponse(
                success=True, message="Connection successful", latency_ms=latency)
        except Exception as exc:
            TerraLogUtil.warning(
                "oracle_connection_test_failed", error=str(exc))
            return DbConfigTestResponse(
                success=False, message=str(exc), latency_ms=None)

    def get_tables(self, host: str, port: int, database: str,
                   username: str, password: str,
                   schema: str = "", extra_params: str = "",
                   ) -> List[dict]:
        url = self.build_connection_url(
            host, port, database, username, password, schema, extra_params)
        owner = self._effective_schema(schema, username)
        engine = create_engine(url)
        try:
            with engine.connect() as conn:
                rows = conn.execute(sa_text(
                    "SELECT table_name, comments "
                    "FROM ALL_TAB_COMMENTS "
                    "WHERE owner = UPPER(:schema) "
                    "ORDER BY table_name"
                ), {"schema": owner}).fetchall()
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
        owner = self._effective_schema(schema, username)
        engine = create_engine(url)
        try:
            with engine.connect() as conn:
                rows = conn.execute(sa_text(
                    "SELECT tc.column_name, tc.data_type, cc.comments, "
                    "CASE WHEN EXISTS ("
                    "  SELECT 1 FROM ALL_CONS_COLUMNS acc "
                    "  JOIN ALL_CONSTRAINTS ac ON ac.constraint_name = acc.constraint_name "
                    "    AND ac.owner = acc.owner "
                    "  WHERE ac.constraint_type = 'P' AND ac.owner = UPPER(:schema) "
                    "    AND ac.table_name = :table AND acc.column_name = tc.column_name"
                    ") THEN 1 ELSE 0 END AS is_pk, "
                    "CASE WHEN tc.nullable = 'Y' THEN 1 ELSE 0 END AS is_nullable "
                    "FROM ALL_TAB_COLUMNS tc "
                    "LEFT JOIN ALL_COL_COMMENTS cc "
                    "  ON cc.owner = tc.owner AND cc.table_name = tc.table_name "
                    "  AND cc.column_name = tc.column_name "
                    "WHERE tc.owner = UPPER(:schema) AND tc.table_name = :table "
                    "ORDER BY tc.column_id"
                ), {"schema": owner, "table": table_name}).fetchall()
            return [{
                "column_name": r[0],
                "column_type": r[1] or "",
                "column_comment": r[2] or "",
                "is_primary_key": bool(r[3]),
                "is_nullable": bool(r[4]),
            } for r in rows]
        finally:
            engine.dispose()
