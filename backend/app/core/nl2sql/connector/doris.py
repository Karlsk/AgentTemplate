"""Apache Doris database connector (MySQL-compatible)."""

import time
from typing import List
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text as sa_text

from app.core.common.logging import TerraLogUtil
from app.core.nl2sql.connector.base import DatabaseConnector
from app.schemas.nl2sql import DbConfigTestResponse


class DorisConnector(DatabaseConnector):
    """Connector for Apache Doris databases (MySQL-compatible)."""

    @property
    def db_type(self) -> str:
        return "doris"

    @property
    def default_port(self) -> int:
        return 9030

    def build_connection_url(self, host: str, port: int, database: str,
                             username: str, password: str,
                             schema: str = "", extra_params: str = "",
                             ) -> str:
        user = quote_plus(username)
        pwd = quote_plus(password)
        url = f"mysql+pymysql://{user}:{pwd}@{host}:{port}/{database}?charset=utf8mb4"
        if extra_params:
            url += f"&{extra_params}"
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
                "doris_connection_test_failed", error=str(exc))
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
                    "SELECT TABLE_NAME, TABLE_COMMENT "
                    "FROM information_schema.TABLES "
                    "WHERE TABLE_SCHEMA = :db "
                    "ORDER BY TABLE_NAME"
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
                    "SELECT COLUMN_NAME, COLUMN_TYPE, COLUMN_COMMENT, "
                    "COLUMN_KEY, IS_NULLABLE "
                    "FROM information_schema.COLUMNS "
                    "WHERE TABLE_SCHEMA = :db AND TABLE_NAME = :table "
                    "ORDER BY ORDINAL_POSITION"
                ), {"db": database, "table": table_name}).fetchall()
            return [{
                "column_name": r[0],
                "column_type": r[1] or "",
                "column_comment": r[2] or "",
                "is_primary_key": r[3] == "PRI",
                "is_nullable": r[4] == "YES",
            } for r in rows]
        finally:
            engine.dispose()
