"""M-Schema formatter for NL2SQL LLM prompts.

Generates a structured Markdown representation of database schema
that LLMs can use to understand table structure for SQL generation.
"""

from typing import List

from app.schemas.nl2sql import SchemaColumnInfo, SchemaTableInfo


def format_table_to_mschema(table: SchemaTableInfo) -> str:
    """Format a single table's metadata into M-Schema format.

    Example output::

        # Table: public.users, User information table
        [
        (id:bigint, User ID, PK),
        (name:varchar, User name),
        (email:varchar, Email address)
        ]

    Args:
        table: Table metadata with columns.

    Returns:
        M-Schema formatted string for one table.
    """
    parts = []

    # Table header
    qualified_name = table.table_name
    if table.table_schema:
        qualified_name = f"{table.table_schema}.{table.table_name}"

    header = f"# Table: {qualified_name}"
    if table.table_comment:
        header += f", {table.table_comment}"
    parts.append(header)

    # Columns
    if table.columns:
        parts.append("[")
        col_lines = []
        for col in table.columns:
            col_str = f"({col.column_name}:{col.column_type or 'unknown'}"
            extras = []
            if col.column_comment:
                extras.append(col.column_comment)
            if col.is_primary_key:
                extras.append("PK")
            if extras:
                col_str += f", {', '.join(extras)}"
            col_str += ")"
            col_lines.append(col_str)
        parts.append(",\n".join(col_lines))
        parts.append("]")

    return "\n".join(parts)


def format_schema_to_mschema(tables: List[SchemaTableInfo],
                             db_schema: str = "") -> str:
    """Format multiple tables into full M-Schema format.

    Example output::

        【DB_ID】 public
        【Schema】
        # Table: public.users, User information table
        [
        (id:bigint, User ID, PK),
        (name:varchar, User name)
        ]

        # Table: public.orders, Order table
        [
        (order_id:bigint, Order ID, PK),
        (user_id:bigint, User ID)
        ]

    Args:
        tables: List of table metadata.
        db_schema: Database schema name for the header.

    Returns:
        Complete M-Schema formatted string.
    """
    parts = []

    if db_schema:
        parts.append(f"【DB_ID】 {db_schema}")
    parts.append("【Schema】")

    for table in tables:
        parts.append(format_table_to_mschema(table))
        parts.append("")  # blank line between tables

    return "\n".join(parts)


def generate_ddl_text(table: SchemaTableInfo, db_type: str = "") -> str:
    """Generate a DDL-like text description for a table.

    This is used as the content for DDL training data entries,
    not actual executable DDL.

    Args:
        table: Table metadata with columns.
        db_type: Database type for dialect hints.

    Returns:
        DDL text description.
    """
    return format_table_to_mschema(table)


def build_compact_embedding_text(table: SchemaTableInfo) -> str:
    """Build a short text for compact DDL embedding mode.

    In compact mode only the table name and description are embedded
    for semantic search, while the full M-Schema DDL is stored as
    training_data.content and returned to the LLM on match.

    Args:
        table: Table metadata.

    Returns:
        ``"{table_name}: {table_comment}"`` or just ``"{table_name}"``
        when no comment exists.
    """
    if table.table_comment:
        return f"{table.table_name}: {table.table_comment}"
    return table.table_name
