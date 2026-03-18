"""NL2SQL API routes — DB config, instance, training data, and search.

All endpoints are workspace-scoped via the current user's ``oid``.
"""

from typing import List, Optional, Union

from fastapi import APIRouter, Body, Path, Query, Request

from app.core.common.deps import CurrentUser, SessionDep
from app.core.common.limiter import limiter
from app.schemas.nl2sql import (
    AddDocumentationRequest,
    AddDDLRequest,
    AddQuestionSQLRequest,
    DbConfigCreate,
    DbConfigListItem,
    DbConfigResponse,
    DbConfigTestRequest,
    DbConfigTestResponse,
    DbConfigUpdate,
    DeleteSchemaTableResponse,
    DiscoverTableItem,
    DiscoverTablesResponse,
    NL2SQLInstanceCreate,
    NL2SQLInstanceListItem,
    NL2SQLInstanceResponse,
    NL2SQLInstanceUpdate,
    NL2SQLSearchRequest,
    NL2SQLSearchResponse,
    SchemaTableInfo,
    SchemaSyncRequest,
    SchemaSyncResponse,
    TrainingDataListItem,
    TrainingDataResponse,
    UpdateSchemaTableRequest,
)
from app.services.nl2sql import NL2SQLService


router = APIRouter(tags=["nl2sql"], prefix="/nl2sql")
nl2sql_service = NL2SQLService()


# ==================== DB Config ====================


@router.post(
    "/db-config",
    response_model=DbConfigResponse,
    summary="create_db_config",
)
@limiter.limit("30/minute")
async def create_db_config(
    request: Request,
    info: DbConfigCreate,
    current_user: CurrentUser,
    session: SessionDep,
):
    """Create a new database configuration."""
    return await nl2sql_service.create_db_config(
        session=session, workspace_id=_ws(current_user), info=info,
    )


@router.put(
    "/db-config",
    response_model=DbConfigResponse,
    summary="update_db_config",
)
@limiter.limit("30/minute")
async def update_db_config(
    request: Request,
    info: DbConfigUpdate,
    current_user: CurrentUser,
    session: SessionDep,
):
    """Update an existing database configuration."""
    return await nl2sql_service.update_db_config(
        session=session, workspace_id=_ws(current_user), info=info,
    )


@router.delete("/db-config/{config_id}", summary="delete_db_config")
@limiter.limit("10/minute")
async def delete_db_config(
    request: Request,
    current_user: CurrentUser,
    session: SessionDep,
    config_id: int = Path(...),
):
    """Delete a database configuration."""
    return await nl2sql_service.delete_db_config(
        session=session, workspace_id=_ws(current_user), config_id=config_id,
    )


@router.get(
    "/db-config/{config_id}",
    response_model=DbConfigResponse,
    summary="get_db_config",
)
@limiter.limit("50/minute")
async def get_db_config(
    request: Request,
    current_user: CurrentUser,
    session: SessionDep,
    config_id: int = Path(...),
):
    """Get a single database configuration by ID."""
    return await nl2sql_service.get_db_config(
        session=session, workspace_id=_ws(current_user), config_id=config_id,
    )


@router.get(
    "/db-config",
    response_model=List[DbConfigListItem],
    summary="list_db_configs",
)
@limiter.limit("50/minute")
async def list_db_configs(
    request: Request,
    current_user: CurrentUser,
    session: SessionDep,
    keyword: Union[str, None] = Query(default=None, max_length=255),
):
    """List database configurations in the current workspace."""
    return await nl2sql_service.list_db_configs(
        session=session, workspace_id=_ws(current_user), keyword=keyword,
    )


@router.post(
    "/db-config/test",
    response_model=DbConfigTestResponse,
    summary="test_db_connection",
)
@limiter.limit("20/minute")
async def test_db_connection(
    request: Request,
    info: DbConfigTestRequest,
    current_user: CurrentUser,
    session: SessionDep,
):
    """Test a database connection without persisting."""
    return await nl2sql_service.test_db_connection(
        session=session, workspace_id=_ws(current_user), info=info,
    )


@router.post(
    "/db-config/{config_id}/test",
    response_model=DbConfigTestResponse,
    summary="test_db_config_by_id",
)
@limiter.limit("20/minute")
async def test_db_config_by_id(
    request: Request,
    current_user: CurrentUser,
    session: SessionDep,
    config_id: int = Path(...),
):
    """Test a saved database configuration and update its status."""
    return await nl2sql_service.test_db_config_by_id(
        session=session, workspace_id=_ws(current_user), config_id=config_id,
    )


# ==================== NL2SQL Instance ====================


@router.post(
    "/instance",
    response_model=NL2SQLInstanceResponse,
    summary="create_instance",
)
@limiter.limit("30/minute")
async def create_instance(
    request: Request,
    info: NL2SQLInstanceCreate,
    current_user: CurrentUser,
    session: SessionDep,
):
    """Create a new NL2SQL instance."""
    return await nl2sql_service.create_instance(
        session=session, workspace_id=_ws(current_user), info=info,
    )


@router.put(
    "/instance",
    response_model=NL2SQLInstanceResponse,
    summary="update_instance",
)
@limiter.limit("30/minute")
async def update_instance(
    request: Request,
    info: NL2SQLInstanceUpdate,
    current_user: CurrentUser,
    session: SessionDep,
):
    """Update an existing NL2SQL instance."""
    return await nl2sql_service.update_instance(
        session=session, workspace_id=_ws(current_user), info=info,
    )


@router.delete("/instance/{instance_id}", summary="delete_instance")
@limiter.limit("10/minute")
async def delete_instance(
    request: Request,
    current_user: CurrentUser,
    session: SessionDep,
    instance_id: int = Path(...),
):
    """Delete an NL2SQL instance and all associated data."""
    return await nl2sql_service.delete_instance(
        session=session, workspace_id=_ws(current_user), instance_id=instance_id,
    )


@router.get(
    "/instance/{instance_id}",
    response_model=NL2SQLInstanceResponse,
    summary="get_instance",
)
@limiter.limit("50/minute")
async def get_instance(
    request: Request,
    current_user: CurrentUser,
    session: SessionDep,
    instance_id: int = Path(...),
):
    """Get a single NL2SQL instance by ID."""
    return await nl2sql_service.get_instance(
        session=session, workspace_id=_ws(current_user), instance_id=instance_id,
    )


@router.get(
    "/instance",
    response_model=List[NL2SQLInstanceListItem],
    summary="list_instances",
)
@limiter.limit("50/minute")
async def list_instances(
    request: Request,
    current_user: CurrentUser,
    session: SessionDep,
    keyword: Union[str, None] = Query(default=None, max_length=255),
):
    """List NL2SQL instances in the current workspace."""
    return await nl2sql_service.list_instances(
        session=session, workspace_id=_ws(current_user), keyword=keyword,
    )


# ==================== Schema ====================


@router.get(
    "/instance/{instance_id}/discover-tables",
    response_model=DiscoverTablesResponse,
    summary="discover_tables",
)
@limiter.limit("10/minute")
async def discover_tables(
    request: Request,
    current_user: CurrentUser,
    session: SessionDep,
    instance_id: int = Path(...),
):
    """Discover tables from the target database without fetching columns."""
    return await nl2sql_service.discover_tables(
        session=session, workspace_id=_ws(current_user), instance_id=instance_id,
    )


@router.post(
    "/instance/{instance_id}/sync-schema",
    response_model=SchemaSyncResponse,
    summary="sync_schema",
)
@limiter.limit("10/minute")
async def sync_schema(
    request: Request,
    current_user: CurrentUser,
    session: SessionDep,
    instance_id: int = Path(...),
    info: Optional[SchemaSyncRequest] = Body(default=None),
):
    """Sync schema from database to instance and generate DDL training data.

    If request body with table_names is provided, only sync those tables.
    If no body or table_names is None, sync all tables.
    """
    table_names = info.table_names if info else None
    return await nl2sql_service.sync_schema(
        session=session,
        workspace_id=_ws(current_user),
        instance_id=instance_id,
        table_names=table_names,
    )


@router.get(
    "/instance/{instance_id}/schema",
    response_model=List[SchemaTableInfo],
    summary="get_schema_tables",
)
@limiter.limit("50/minute")
async def get_schema_tables(
    request: Request,
    current_user: CurrentUser,
    session: SessionDep,
    instance_id: int = Path(...),
):
    """Get synced schema tables for an instance."""
    return await nl2sql_service.get_schema_tables(
        session=session, workspace_id=_ws(current_user), instance_id=instance_id,
    )


@router.get(
    "/db-config/{config_id}/discover-tables",
    response_model=List[DiscoverTableItem],
    summary="discover_tables_by_config",
)
@limiter.limit("10/minute")
async def discover_tables_by_config(
    request: Request,
    current_user: CurrentUser,
    session: SessionDep,
    config_id: int = Path(...),
):
    """Discover tables from a DB config (before instance exists).

    Used during instance creation wizard step 2.
    """
    return await nl2sql_service.discover_tables_by_config(
        session=session, workspace_id=_ws(current_user), config_id=config_id,
    )


@router.put(
    "/instance/{instance_id}/schema-table/{table_name}",
    response_model=SchemaTableInfo,
    summary="update_schema_table",
)
@limiter.limit("20/minute")
async def update_schema_table(
    request: Request,
    info: UpdateSchemaTableRequest,
    current_user: CurrentUser,
    session: SessionDep,
    instance_id: int = Path(...),
    table_name: str = Path(..., max_length=255),
):
    """Update a schema table's description and columns."""
    return await nl2sql_service.update_schema_table(
        session=session,
        workspace_id=_ws(current_user),
        instance_id=instance_id,
        table_name=table_name,
        info=info,
    )


@router.delete(
    "/instance/{instance_id}/schema-table/{table_name}",
    response_model=DeleteSchemaTableResponse,
    summary="delete_schema_table",
)
@limiter.limit("10/minute")
async def delete_schema_table(
    request: Request,
    current_user: CurrentUser,
    session: SessionDep,
    instance_id: int = Path(...),
    table_name: str = Path(..., max_length=255),
):
    """Delete a schema table with cascade cleanup."""
    return await nl2sql_service.delete_schema_table(
        session=session,
        workspace_id=_ws(current_user),
        instance_id=instance_id,
        table_name=table_name,
    )


# ==================== Training Data ====================


@router.post(
    "/instance/{instance_id}/ddl",
    response_model=TrainingDataResponse,
    summary="add_ddl",
)
@limiter.limit("30/minute")
async def add_ddl(
    request: Request,
    info: AddDDLRequest,
    current_user: CurrentUser,
    session: SessionDep,
    instance_id: int = Path(...),
):
    """Add a DDL training data entry."""
    return await nl2sql_service.add_ddl(
        session=session, workspace_id=_ws(current_user),
        instance_id=instance_id, info=info,
    )


@router.post(
    "/instance/{instance_id}/sql",
    response_model=TrainingDataResponse,
    summary="add_question_sql",
)
@limiter.limit("30/minute")
async def add_question_sql(
    request: Request,
    info: AddQuestionSQLRequest,
    current_user: CurrentUser,
    session: SessionDep,
    instance_id: int = Path(...),
):
    """Add a question-SQL pair training data entry."""
    return await nl2sql_service.add_question_sql(
        session=session, workspace_id=_ws(current_user),
        instance_id=instance_id, info=info,
    )


@router.post(
    "/instance/{instance_id}/doc",
    response_model=TrainingDataResponse,
    summary="add_documentation",
)
@limiter.limit("30/minute")
async def add_documentation(
    request: Request,
    info: AddDocumentationRequest,
    current_user: CurrentUser,
    session: SessionDep,
    instance_id: int = Path(...),
):
    """Add a documentation/glossary training data entry."""
    return await nl2sql_service.add_documentation(
        session=session, workspace_id=_ws(current_user),
        instance_id=instance_id, info=info,
    )


@router.delete(
    "/instance/{instance_id}/training-data/{training_data_id}",
    summary="delete_training_data",
)
@limiter.limit("30/minute")
async def delete_training_data(
    request: Request,
    current_user: CurrentUser,
    session: SessionDep,
    instance_id: int = Path(...),
    training_data_id: int = Path(...),
):
    """Delete a training data entry and its vector."""
    return await nl2sql_service.delete_training_data(
        session=session, workspace_id=_ws(current_user),
        instance_id=instance_id, training_data_id=training_data_id,
    )


@router.get(
    "/instance/{instance_id}/training-data",
    summary="list_training_data",
)
@limiter.limit("50/minute")
async def list_training_data(
    request: Request,
    current_user: CurrentUser,
    session: SessionDep,
    instance_id: int = Path(...),
    data_type: Optional[str] = Query(default=None, pattern="^(ddl|sql|doc)$"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
):
    """List training data for an instance with pagination."""
    items, total = await nl2sql_service.list_training_data(
        session=session, workspace_id=_ws(current_user),
        instance_id=instance_id, data_type=data_type,
        offset=offset, limit=limit,
    )
    return {
        "items": items,
        "total": total,
        "offset": offset,
        "limit": limit,
    }


# ==================== Search ====================


@router.post(
    "/search",
    response_model=NL2SQLSearchResponse,
    summary="nl2sql_search",
)
@limiter.limit("30/minute")
async def nl2sql_search(
    request: Request,
    body: NL2SQLSearchRequest,
    current_user: CurrentUser,
    session: SessionDep,
):
    """Search for similar SQL examples, related DDL, and documentation."""
    return await nl2sql_service.search(
        session=session, workspace_id=_ws(current_user), request=body,
    )


# ==================== Helpers ====================


def _ws(user) -> int:
    """Extract workspace_id from current_user."""
    if isinstance(user, dict):
        return user.get("oid", 1)
    return getattr(user, "oid", 1)
