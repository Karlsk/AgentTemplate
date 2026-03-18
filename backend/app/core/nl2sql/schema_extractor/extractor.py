"""Unified schema extraction entry point.

Orchestrates the extraction of full database schema via a connector
and syncs it to the local nl2sql_schema_meta table.
"""

from typing import List, Optional, Set

from sqlmodel import Session, select

from app.core.common.logging import TerraLogUtil
from app.core.nl2sql.connector.base import DatabaseConnector
from app.models.nl2sql import NL2SQLSchemaMetaModel
from app.schemas.nl2sql import SchemaColumnInfo, SchemaTableInfo, SchemaSyncResponse


def extract_full_schema(
    connector: DatabaseConnector,
    host: str,
    port: int,
    database: str,
    username: str,
    password: str,
    schema: str = "",
    extra_params: str = "",
    table_names: Optional[List[str]] = None,
) -> List[SchemaTableInfo]:
    """Extract full schema (tables + columns) from a live database.

    Args:
        connector: Database connector instance.
        host: Database host.
        port: Database port.
        database: Database name.
        username: Connection username.
        password: Connection password (plaintext).
        schema: Database schema/namespace.
        extra_params: Extra connection parameters.
        table_names: If provided, only extract these tables. None = all tables.

    Returns:
        List of SchemaTableInfo with nested columns.
    """
    tables_raw = connector.get_tables(
        host, port, database, username, password, schema, extra_params)

    # Filter to selected tables if specified
    if table_names is not None:
        wanted: Set[str] = set(table_names)
        tables_raw = [t for t in tables_raw if t["table_name"] in wanted]

    result: List[SchemaTableInfo] = []
    for t in tables_raw:
        table_name = t["table_name"]
        table_comment = t.get("table_comment", "")

        columns_raw = connector.get_columns(
            host, port, database, username, password,
            table_name, schema, extra_params)

        columns = [
            SchemaColumnInfo(
                column_name=c["column_name"],
                column_type=c.get("column_type", ""),
                column_comment=c.get("column_comment", ""),
                is_primary_key=c.get("is_primary_key", False),
                is_nullable=c.get("is_nullable", True),
            )
            for c in columns_raw
        ]

        result.append(SchemaTableInfo(
            table_schema=schema or None,
            table_name=table_name,
            table_comment=table_comment or None,
            columns=columns,
        ))

    TerraLogUtil.info(
        "schema_extracted",
        table_count=len(result),
        column_count=sum(len(t.columns) for t in result),
    )
    return result


def sync_schema_to_db(
    session: Session,
    instance_id: int,
    db_config_id: int,
    workspace_id: int,
    tables: List[SchemaTableInfo],
    table_names: Optional[List[str]] = None,
) -> SchemaSyncResponse:
    """Sync extracted schema metadata to nl2sql_schema_meta table.

    When table_names is None, performs a full replace (delete all + insert).
    When table_names is provided, performs a selective replace (only delete/insert
    rows for the specified tables, preserving other tables).

    Args:
        session: Database session.
        instance_id: NL2SQL instance ID.
        db_config_id: DB config ID.
        workspace_id: Workspace ID.
        tables: Extracted schema tables.
        table_names: If provided, only replace rows for these tables.

    Returns:
        SchemaSyncResponse with counts.
    """
    if table_names is not None:
        # Selective mode: only delete rows for the specified tables
        target_set: Set[str] = set(table_names)
        existing = session.exec(
            select(NL2SQLSchemaMetaModel).where(
                NL2SQLSchemaMetaModel.instance_id == instance_id,
                NL2SQLSchemaMetaModel.table_name.in_(target_set),
            )
        ).all()
    else:
        # Full replace: delete all rows for this instance
        existing = session.exec(
            select(NL2SQLSchemaMetaModel).where(
                NL2SQLSchemaMetaModel.instance_id == instance_id)
        ).all()

    for row in existing:
        session.delete(row)
    session.flush()

    total_columns = 0
    for table in tables:
        # Insert table-level row
        table_row = NL2SQLSchemaMetaModel(
            instance_id=instance_id,
            db_config_id=db_config_id,
            workspace_id=workspace_id,
            table_schema=table.table_schema,
            table_name=table.table_name,
            table_comment=table.table_comment,
            column_name=None,
            column_type=None,
            column_comment=None,
        )
        session.add(table_row)

        # Insert column-level rows
        for col in table.columns:
            col_row = NL2SQLSchemaMetaModel(
                instance_id=instance_id,
                db_config_id=db_config_id,
                workspace_id=workspace_id,
                table_schema=table.table_schema,
                table_name=table.table_name,
                table_comment=table.table_comment,
                column_name=col.column_name,
                column_type=col.column_type,
                column_comment=col.column_comment,
                is_primary_key=col.is_primary_key,
                is_nullable=col.is_nullable,
            )
            session.add(col_row)
            total_columns += 1

    session.commit()

    TerraLogUtil.info(
        "schema_synced_to_db",
        instance_id=instance_id,
        tables=len(tables),
        columns=total_columns,
        selective=table_names is not None,
    )
    return SchemaSyncResponse(
        instance_id=instance_id,
        tables_synced=len(tables),
        columns_synced=total_columns,
        ddl_generated=0,  # Updated by caller after DDL generation
    )
