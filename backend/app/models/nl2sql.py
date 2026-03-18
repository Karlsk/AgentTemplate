"""NL2SQL database models.

Stores DB connection configs, NL2SQL instances, training data metadata,
and synced schema metadata. Vector embeddings are stored in dynamic
per-instance pgvector tables managed by NL2SQLVectorStore.
"""

from typing import Optional

from sqlalchemy import BigInteger, Text
from sqlmodel import Field

from app.models.base import BaseModel


class NL2SQLDbConfigModel(BaseModel, table=True):
    """Database connection configuration for NL2SQL.

    Attributes:
        id: Primary key.
        workspace_id: Owning workspace.
        name: Display name (unique within workspace).
        db_type: Database type identifier.
        host: Database host.
        port: Database port.
        database_name: Target database name.
        schema_name: Schema/namespace (PG, Oracle, etc.).
        username: Connection username.
        encrypted_password: base64-encrypted password.
        extra_params: JSON extra connection parameters.
        status: 0=unverified, 1=ok, 2=failed.
    """

    __tablename__ = "nl2sql_db_config"

    id: int = Field(default=None, primary_key=True)
    workspace_id: int = Field(nullable=False, sa_type=BigInteger(), index=True)
    name: str = Field(max_length=255, nullable=False)
    db_type: str = Field(max_length=32, nullable=False)
    host: str = Field(max_length=512, nullable=False)
    port: int = Field(nullable=False)
    database_name: str = Field(max_length=255, nullable=False)
    schema_name: Optional[str] = Field(
        default=None, max_length=255, nullable=True)
    username: str = Field(max_length=255, nullable=False)
    encrypted_password: str = Field(nullable=False, sa_type=Text())
    extra_params: Optional[str] = Field(default=None, sa_type=Text())
    status: int = Field(default=0, nullable=False)


class NL2SQLInstanceModel(BaseModel, table=True):
    """NL2SQL instance, each linked to a DB config and embedding model.

    Attributes:
        id: Primary key.
        workspace_id: Owning workspace.
        name: Instance display name.
        description: Free-text description.
        db_config_id: FK to nl2sql_db_config.
        embedding_model_id: Optional FK to ai_model.
        ddl_mode: DDL embedding strategy ('full' or 'compact').
        ddl_count: Cached DDL entry count.
        sql_count: Cached SQL pair count.
        doc_count: Cached documentation count.
        status: 0=init, 1=ready, 2=syncing.
    """

    __tablename__ = "nl2sql_instance"

    id: int = Field(default=None, primary_key=True)
    workspace_id: int = Field(nullable=False, sa_type=BigInteger(), index=True)
    name: str = Field(max_length=255, nullable=False)
    description: str = Field(default="", sa_type=Text())
    db_config_id: int = Field(nullable=False, index=True)
    embedding_model_id: Optional[int] = Field(default=None, nullable=True)
    ddl_mode: str = Field(default="full", max_length=16, nullable=False)
    ddl_count: int = Field(default=0, nullable=False)
    sql_count: int = Field(default=0, nullable=False)
    doc_count: int = Field(default=0, nullable=False)
    status: int = Field(default=0, nullable=False)


class NL2SQLTrainingDataModel(BaseModel, table=True):
    """Training data record for NL2SQL (DDL, SQL pair, or documentation).

    Attributes:
        id: Primary key.
        instance_id: FK to nl2sql_instance.
        workspace_id: Denormalised for fast filtering.
        data_type: 'ddl', 'sql', or 'doc'.
        content: Main text content (DDL statement or doc text).
        question: Natural language question (sql type only).
        sql_text: Corresponding SQL (sql type only).
        table_name: Associated table name (ddl type).
        source: 'auto_sync' or 'manual'.
        status: 0=pending_embed, 1=embedded, 2=failed.
    """

    __tablename__ = "nl2sql_training_data"

    id: int = Field(default=None, primary_key=True)
    instance_id: int = Field(nullable=False, index=True)
    workspace_id: int = Field(nullable=False, sa_type=BigInteger(), index=True)
    data_type: str = Field(max_length=16, nullable=False)
    content: str = Field(nullable=False, sa_type=Text())
    question: Optional[str] = Field(default=None, sa_type=Text())
    sql_text: Optional[str] = Field(default=None, sa_type=Text())
    table_name: Optional[str] = Field(
        default=None, max_length=255, nullable=True)
    source: str = Field(default="manual", max_length=32, nullable=False)
    status: int = Field(default=0, nullable=False)


class NL2SQLSchemaMetaModel(BaseModel, table=True):
    """Schema metadata synced from a live database.

    When column_name is NULL, the row represents table-level metadata.
    When column_name is set, it represents a column within that table.

    Attributes:
        id: Primary key.
        instance_id: FK to nl2sql_instance.
        db_config_id: FK to nl2sql_db_config.
        workspace_id: Owning workspace.
        table_schema: Database schema/namespace.
        table_name: Table name.
        table_comment: Table comment/description.
        column_name: Column name (NULL for table-level row).
        column_type: Column data type.
        column_comment: Column comment/description.
        is_primary_key: Whether the column is a primary key.
        is_nullable: Whether the column allows NULL.
    """

    __tablename__ = "nl2sql_schema_meta"

    id: int = Field(default=None, primary_key=True)
    instance_id: int = Field(nullable=False, index=True)
    db_config_id: int = Field(nullable=False, index=True)
    workspace_id: int = Field(nullable=False, sa_type=BigInteger())
    table_schema: Optional[str] = Field(
        default=None, max_length=255, nullable=True)
    table_name: str = Field(max_length=255, nullable=False)
    table_comment: Optional[str] = Field(default=None, sa_type=Text())
    column_name: Optional[str] = Field(
        default=None, max_length=255, nullable=True)
    column_type: Optional[str] = Field(
        default=None, max_length=128, nullable=True)
    column_comment: Optional[str] = Field(default=None, sa_type=Text())
    is_primary_key: bool = Field(default=False, nullable=False)
    is_nullable: bool = Field(default=True, nullable=False)
