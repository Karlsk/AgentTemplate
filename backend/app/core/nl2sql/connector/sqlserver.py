"""SQL Server database connector."""

import time
from typing import List
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text as sa_text

from app.core.common.logging import TerraLogUtil
from app.core.nl2sql.connector.base import DatabaseConnector
from app.schemas.nl2sql import DbConfigTestResponse


class SQLServerConnector(DatabaseConnector):
    """Connector for Microsoft SQL Server databases."""

    @property
    def db_type(self) -> str:
        return "sqlserver"

    @property
    def default_port(self) -> int:
        return 1433

    def build_connection_url(self, host: str, port: int, database: str,
                             username: str, password: str,
                             schema: str = "", extra_params: str = "",
                             ) -> str:
        user = quote_plus(username)
        pwd = quote_plus(password)
        url = f"mssql+pymssql://{user}:{pwd}@{host}:{port}/{database}"
        if extra_params:
            url += f"?{extra_params}"
        return url

    def _effective_schema(self, schema: str) -> str:
        return schema or "dbo"

    def test_connection(self, host: str, port: int, database: str,
                        username: str, password: str,
                        schema: str = "", extra_params: str = "",
                        ) -> DbConfigTestResponse:
        url = self.build_connection_url(
            host, port, database, username, password, schema, extra_params)
        try:
            engine = create_engine(url, connect_args={"login_timeout": 10})
            t0 = time.perf_counter()
            with engine.connect() as conn:
                conn.execute(sa_text("SELECT 1"))
            latency = round((time.perf_counter() - t0) * 1000, 2)
            engine.dispose()
            return DbConfigTestResponse(
                success=True, message="Connection successful", latency_ms=latency)
        except Exception as exc:
            TerraLogUtil.warning(
                "sqlserver_connection_test_failed", error=str(exc))
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
                    "CAST(ep.value AS NVARCHAR(4000)) AS table_comment "
                    "FROM INFORMATION_SCHEMA.TABLES t "
                    "LEFT JOIN sys.tables st "
                    "  ON st.name = t.TABLE_NAME AND SCHEMA_NAME(st.schema_id) = t.TABLE_SCHEMA "
                    "LEFT JOIN sys.extended_properties ep "
                    "  ON ep.major_id = st.object_id AND ep.minor_id = 0 AND ep.name = 'MS_Description' "
                    "WHERE t.TABLE_SCHEMA = :schema AND t.TABLE_TYPE = 'BASE TABLE' "
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
                    "CAST(ep.value AS NVARCHAR(4000)) AS column_comment, "
                    "CASE WHEN kcu.COLUMN_NAME IS NOT NULL THEN 1 ELSE 0 END AS is_pk, "
                    "CASE WHEN c.IS_NULLABLE = 'YES' THEN 1 ELSE 0 END AS is_nullable "
                    "FROM INFORMATION_SCHEMA.COLUMNS c "
                    "LEFT JOIN sys.columns sc "
                    "  ON sc.name = c.COLUMN_NAME "
                    "  AND sc.object_id = OBJECT_ID(:schema + '.' + :table) "
                    "LEFT JOIN sys.extended_properties ep "
                    "  ON ep.major_id = sc.object_id AND ep.minor_id = sc.column_id "
                    "  AND ep.name = 'MS_Description' "
                    "LEFT JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu "
                    "  ON kcu.TABLE_SCHEMA = c.TABLE_SCHEMA AND kcu.TABLE_NAME = c.TABLE_NAME "
                    "  AND kcu.COLUMN_NAME = c.COLUMN_NAME "
                    "  AND EXISTS ("
                    "    SELECT 1 FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc "
                    "    WHERE tc.CONSTRAINT_TYPE = 'PRIMARY KEY' "
                    "    AND tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME "
                    "    AND tc.TABLE_SCHEMA = kcu.TABLE_SCHEMA"
                    "  ) "
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
