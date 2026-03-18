"""ClickHouse database connector."""

import time
from typing import List
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text as sa_text

from app.core.common.logging import TerraLogUtil
from app.core.nl2sql.connector.base import DatabaseConnector
from app.schemas.nl2sql import DbConfigTestResponse


class ClickHouseConnector(DatabaseConnector):
    """Connector for ClickHouse databases."""

    @property
    def db_type(self) -> str:
        return "clickhouse"

    @property
    def default_port(self) -> int:
        return 8123

    def build_connection_url(self, host: str, port: int, database: str,
                             username: str, password: str,
                             schema: str = "", extra_params: str = "",
                             ) -> str:
        user = quote_plus(username)
        pwd = quote_plus(password)
        url = f"clickhouse+http://{user}:{pwd}@{host}:{port}/{database}"
        if extra_params:
            url += f"?{extra_params}"
        return url

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
                "clickhouse_connection_test_failed", error=str(exc))
            return DbConfigTestResponse(
                success=False, message=str(exc), latency_ms=None)

    def get_tables(self, host: str, port: int, database: str,
                   username: str, password: str,
                   schema: str = "", extra_params: str = "",
                   ) -> List[dict]:
        url = self.build_connection_url(
            host, port, database, username, password, schema, extra_params)
        engine = create_engine(url)
        try:
            with engine.connect() as conn:
                rows = conn.execute(sa_text(
                    "SELECT name, comment "
                    "FROM system.tables "
                    "WHERE database = :db "
                    "ORDER BY name"
                ), {"db": database}).fetchall()
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
        engine = create_engine(url)
        try:
            with engine.connect() as conn:
                rows = conn.execute(sa_text(
                    "SELECT name, type, comment, "
                    "is_in_primary_key "
                    "FROM system.columns "
                    "WHERE database = :db AND table = :table "
                    "ORDER BY position"
                ), {"db": database, "table": table_name}).fetchall()
            return [{
                "column_name": r[0],
                "column_type": r[1] or "",
                "column_comment": r[2] or "",
                "is_primary_key": bool(r[3]),
                "is_nullable": False,
            } for r in rows]
        finally:
            engine.dispose()
