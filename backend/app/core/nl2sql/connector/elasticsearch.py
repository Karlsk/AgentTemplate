"""Elasticsearch connector."""

import time
from typing import List
from urllib.parse import quote_plus

import requests

from app.core.common.logging import TerraLogUtil
from app.core.nl2sql.connector.base import DatabaseConnector
from app.schemas.nl2sql import DbConfigTestResponse


class ElasticsearchConnector(DatabaseConnector):
    """Connector for Elasticsearch clusters."""

    @property
    def db_type(self) -> str:
        return "elasticsearch"

    @property
    def default_port(self) -> int:
        return 9200

    def build_connection_url(self, host: str, port: int, database: str,
                             username: str, password: str,
                             schema: str = "", extra_params: str = "",
                             ) -> str:
        if username and password:
            user = quote_plus(username)
            pwd = quote_plus(password)
            url = f"http://{user}:{pwd}@{host}:{port}"
        else:
            url = f"http://{host}:{port}"
        return url

    def _build_base_url(self, host: str, port: int) -> str:
        return f"http://{host}:{port}"

    def _build_auth(self, username: str, password: str) -> tuple:
        if username and password:
            return (username, password)
        return None

    def test_connection(self, host: str, port: int, database: str,
                        username: str, password: str,
                        schema: str = "", extra_params: str = "",
                        ) -> DbConfigTestResponse:
        base_url = self._build_base_url(host, port)
        auth = self._build_auth(username, password)
        try:
            t0 = time.perf_counter()
            resp = requests.get(base_url, auth=auth, timeout=10)
            resp.raise_for_status()
            latency = round((time.perf_counter() - t0) * 1000, 2)
            return DbConfigTestResponse(
                success=True, message="Connection successful", latency_ms=latency)
        except Exception as exc:
            TerraLogUtil.warning(
                "elasticsearch_connection_test_failed", error=str(exc))
            return DbConfigTestResponse(
                success=False, message=str(exc), latency_ms=None)

    def get_tables(self, host: str, port: int, database: str,
                   username: str, password: str,
                   schema: str = "", extra_params: str = "",
                   ) -> List[dict]:
        base_url = self._build_base_url(host, port)
        auth = self._build_auth(username, password)
        try:
            resp = requests.get(
                f"{base_url}/_cat/indices?format=json",
                auth=auth, timeout=30)
            resp.raise_for_status()
            indices = resp.json()
            return [{"table_name": idx.get("index", ""), "table_comment": ""}
                    for idx in indices
                    if not idx.get("index", "").startswith(".")]
        except Exception as exc:
            TerraLogUtil.warning(
                "elasticsearch_get_tables_failed", error=str(exc))
            return []

    def get_columns(self, host: str, port: int, database: str,
                    username: str, password: str,
                    table_name: str,
                    schema: str = "", extra_params: str = "",
                    ) -> List[dict]:
        base_url = self._build_base_url(host, port)
        auth = self._build_auth(username, password)
        try:
            resp = requests.get(
                f"{base_url}/{table_name}/_mapping",
                auth=auth, timeout=30)
            resp.raise_for_status()
            mapping = resp.json()

            columns = []
            index_data = mapping.get(table_name, {})
            properties = index_data.get("mappings", {}).get("properties", {})
            columns = self._flatten_properties(properties)
            return columns
        except Exception as exc:
            TerraLogUtil.warning("elasticsearch_get_columns_failed",
                                 index=table_name, error=str(exc))
            return []

    def _flatten_properties(self, properties: dict,
                            prefix: str = "") -> List[dict]:
        """Flatten nested Elasticsearch mapping properties into column list."""
        columns = []
        for field_name, field_info in sorted(properties.items()):
            full_name = f"{prefix}{field_name}" if not prefix else f"{prefix}.{field_name}"
            field_type = field_info.get("type", "object")
            columns.append({
                "column_name": full_name if prefix else field_name,
                "column_type": field_type,
                "column_comment": "",
                "is_primary_key": False,
                "is_nullable": True,
            })
            # Recurse into nested properties
            nested_props = field_info.get("properties")
            if nested_props:
                nested_prefix = full_name if prefix else field_name
                columns.extend(
                    self._flatten_properties(nested_props, prefix=nested_prefix))
        return columns
