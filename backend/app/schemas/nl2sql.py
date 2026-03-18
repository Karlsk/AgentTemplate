"""Pydantic schemas for the NL2SQL API."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ==================== DB Config ====================

class DbConfigCreate(BaseModel):
    """Create a database configuration."""

    name: str = Field(..., max_length=255)
    db_type: str = Field(
        ..., max_length=32,
        description="mysql/postgresql/oracle/sqlserver/clickhouse/dameng/doris/starrocks/kingbase/redshift/elasticsearch")
    host: str = Field(..., max_length=512)
    port: int = Field(...)
    database_name: str = Field(..., max_length=255)
    schema_name: Optional[str] = Field(default=None, max_length=255)
    username: str = Field(..., max_length=255)
    password: str = Field(...,
                          description="Plaintext password, encrypted server-side")
    extra_params: Optional[str] = Field(default=None)


class DbConfigUpdate(BaseModel):
    """Update a database configuration."""

    id: int
    name: Optional[str] = Field(default=None, max_length=255)
    db_type: Optional[str] = Field(default=None, max_length=32)
    host: Optional[str] = Field(default=None, max_length=512)
    port: Optional[int] = None
    database_name: Optional[str] = Field(default=None, max_length=255)
    schema_name: Optional[str] = Field(default=None, max_length=255)
    username: Optional[str] = Field(default=None, max_length=255)
    password: Optional[str] = Field(default=None)
    extra_params: Optional[str] = None


class DbConfigResponse(BaseModel):
    """Full DB config response (password excluded)."""

    id: int
    workspace_id: int
    name: str
    db_type: str
    host: str
    port: int
    database_name: str
    schema_name: Optional[str] = None
    username: str
    extra_params: Optional[str] = None
    status: int
    created_at: datetime


class DbConfigListItem(BaseModel):
    """DB config list item (lighter)."""

    id: int
    name: str
    db_type: str
    host: str
    port: int
    database_name: str
    status: int
    created_at: datetime


class DbConfigTestRequest(BaseModel):
    """Test a database connection without persisting."""

    db_type: str = Field(..., max_length=32)
    host: str = Field(..., max_length=512)
    port: int = Field(...)
    database_name: str = Field(..., max_length=255)
    schema_name: Optional[str] = Field(default=None, max_length=255)
    username: str = Field(..., max_length=255)
    password: str = Field(...)
    extra_params: Optional[str] = None


class DbConfigTestResponse(BaseModel):
    """Result of a database connection test."""

    success: bool
    message: str
    latency_ms: Optional[float] = None


# ==================== NL2SQL Instance ====================

class NL2SQLInstanceCreate(BaseModel):
    """Create an NL2SQL instance."""

    name: str = Field(..., max_length=255)
    description: str = Field(default="")
    db_config_id: int
    embedding_model_id: Optional[int] = None
    ddl_mode: str = Field(
        default="full", description="DDL embedding mode: 'full' or 'compact'")
    table_names: Optional[List[str]] = Field(
        default=None,
        description="Tables to sync on creation. None = skip initial sync.",
    )


class NL2SQLInstanceUpdate(BaseModel):
    """Update an NL2SQL instance."""

    id: int
    name: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None
    embedding_model_id: Optional[int] = None
    ddl_mode: Optional[str] = Field(
        default=None, description="DDL embedding mode: 'full' or 'compact'")


class NL2SQLInstanceResponse(BaseModel):
    """Full NL2SQL instance response."""

    id: int
    workspace_id: int
    name: str
    description: str
    db_config_id: int
    embedding_model_id: Optional[int] = None
    ddl_mode: str
    ddl_count: int
    sql_count: int
    doc_count: int
    status: int
    created_at: datetime


class NL2SQLInstanceListItem(BaseModel):
    """NL2SQL instance list item (lighter)."""

    id: int
    name: str
    description: str
    db_config_id: int
    ddl_mode: str
    ddl_count: int
    sql_count: int
    doc_count: int
    status: int
    created_at: datetime


class SchemaSyncResponse(BaseModel):
    """Result of a schema sync operation."""

    instance_id: int
    tables_synced: int
    columns_synced: int
    ddl_generated: int


class SchemaSyncRequest(BaseModel):
    """Request body for selective schema sync."""

    table_names: Optional[List[str]] = Field(
        default=None,
        description="Tables to sync. None or empty = sync all tables (backward compatible).",
    )


class DiscoverTableItem(BaseModel):
    """A single table discovered from the target database."""

    table_name: str
    table_comment: Optional[str] = None
    synced: bool = False


class DiscoverTablesResponse(BaseModel):
    """Response for discover-tables endpoint."""

    instance_id: int
    tables: List[DiscoverTableItem]
    total: int


# ==================== Training Data ====================

class AddDDLRequest(BaseModel):
    """Add a DDL entry."""

    content: str = Field(..., min_length=1)
    table_name: Optional[str] = Field(default=None, max_length=255)


class AddQuestionSQLRequest(BaseModel):
    """Add a question-SQL pair."""

    question: str = Field(..., min_length=1)
    sql_text: str = Field(..., min_length=1)


class AddDocumentationRequest(BaseModel):
    """Add a documentation/glossary entry."""

    content: str = Field(..., min_length=1)


class BulkAddDDLRequest(BaseModel):
    """Bulk add DDL entries."""

    items: List[AddDDLRequest] = Field(..., min_length=1)


class BulkAddQuestionSQLRequest(BaseModel):
    """Bulk add question-SQL pairs."""

    items: List[AddQuestionSQLRequest] = Field(..., min_length=1)


class TrainingDataResponse(BaseModel):
    """Full training data response."""

    id: int
    instance_id: int
    data_type: str
    content: str
    question: Optional[str] = None
    sql_text: Optional[str] = None
    table_name: Optional[str] = None
    source: str
    status: int
    created_at: datetime


class TrainingDataListItem(BaseModel):
    """Training data list item."""

    id: int
    data_type: str
    content: str
    question: Optional[str] = None
    sql_text: Optional[str] = None
    table_name: Optional[str] = None
    source: str
    status: int
    created_at: datetime


# ==================== Schema Meta ====================

class SchemaColumnInfo(BaseModel):
    """Column metadata from synced schema."""

    column_name: str
    column_type: Optional[str] = None
    column_comment: Optional[str] = None
    is_primary_key: bool = False
    is_nullable: bool = True


class SchemaTableInfo(BaseModel):
    """Table metadata from synced schema."""

    table_schema: Optional[str] = None
    table_name: str
    table_comment: Optional[str] = None
    columns: List[SchemaColumnInfo] = []


class UpdateSchemaColumnItem(BaseModel):
    """A single column update within a schema table edit."""

    column_name: str
    column_comment: Optional[str] = None


class UpdateSchemaTableRequest(BaseModel):
    """Request body for updating a schema table's metadata."""

    table_comment: Optional[str] = None
    columns: List[UpdateSchemaColumnItem] = Field(
        ...,
        description="Columns to keep. Columns not listed will be deleted from schema_meta.",
    )


class DeleteSchemaTableResponse(BaseModel):
    """Response after deleting a schema table and its related data."""

    table_name: str
    schema_rows_deleted: int
    training_data_deleted: int
    vectors_deleted: int


# ==================== Search ====================

class NL2SQLSearchRequest(BaseModel):
    """NL2SQL similarity search request."""

    instance_id: int
    question: str = Field(..., min_length=1, max_length=2000)
    top_k_ddl: Optional[int] = Field(default=None, ge=1, le=50)
    top_k_sql: Optional[int] = Field(default=None, ge=1, le=50)
    top_k_doc: Optional[int] = Field(default=None, ge=1, le=50)


class SimilarSQLResult(BaseModel):
    """A similar question-SQL pair from search."""

    id: int
    question: str
    sql_text: str
    score: float


class RelatedDDLResult(BaseModel):
    """A related DDL entry from search."""

    id: int
    content: str
    table_name: Optional[str] = None
    score: float


class RelatedDocResult(BaseModel):
    """A related documentation entry from search."""

    id: int
    content: str
    score: float


class NL2SQLSearchResponse(BaseModel):
    """NL2SQL similarity search response."""

    question: str
    similar_sqls: List[SimilarSQLResult]
    related_ddls: List[RelatedDDLResult]
    related_docs: List[RelatedDocResult]
