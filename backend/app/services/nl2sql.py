"""NL2SQL service — DB config, instance, training data, and search operations.

All operations are workspace-scoped.
Uses per-instance pgvector tables for DDL, SQL, and documentation embeddings.
"""

import base64
import json
import time
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from sqlmodel import Session, func, select

from app.core.common.config import settings
from app.core.common.crypt import base64_decrypt, base64_encrypt
from app.core.common.logging import TerraLogUtil
from app.core.nl2sql.connector import factory as connector_factory
from app.core.nl2sql.schema_extractor.extractor import (
    extract_full_schema,
    sync_schema_to_db,
)
from app.core.nl2sql.schema_extractor.mschema import (
    build_compact_embedding_text,
    generate_ddl_text,
)
from app.core.nl2sql.vector_store import (
    VECTOR_TYPE_DDL,
    VECTOR_TYPE_DOC,
    VECTOR_TYPE_SQL,
    add_vector,
    add_vectors_batch,
    create_instance_tables,
    delete_vector_by_training_data_id,
    drop_instance_tables,
    get_vector_count,
    instance_tables_exist,
    search_similar,
)
from app.core.rag.embedding.provider import (
    DEFAULT_SAFE_BATCH_SIZE,
    EmbeddingModelCapability,
    EmbeddingProviderRegistry,
    probe_embedding_dimension,
)
from app.models.ai_model import AiModelDetail
from app.models.nl2sql import (
    NL2SQLDbConfigModel,
    NL2SQLInstanceModel,
    NL2SQLSchemaMetaModel,
    NL2SQLTrainingDataModel,
)
from app.schemas.nl2sql import (
    AddDocumentationRequest,
    AddDDLRequest,
    AddQuestionSQLRequest,
    BulkAddDDLRequest,
    BulkAddQuestionSQLRequest,
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
    RelatedDDLResult,
    RelatedDocResult,
    SchemaColumnInfo,
    SchemaTableInfo,
    SchemaSyncResponse,
    SimilarSQLResult,
    TrainingDataListItem,
    TrainingDataResponse,
    UpdateSchemaTableRequest,
)


class NL2SQLService:
    """Service for workspace-scoped NL2SQL operations."""

    # ====================== DB Config CRUD ======================

    @staticmethod
    async def create_db_config(
        *,
        session: Session,
        workspace_id: int,
        info: DbConfigCreate,
    ) -> DbConfigResponse:
        """Create a new database configuration."""
        existing = session.exec(
            select(NL2SQLDbConfigModel).where(
                NL2SQLDbConfigModel.workspace_id == workspace_id,
                NL2SQLDbConfigModel.name == info.name,
            )
        ).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"DB config '{info.name}' already exists in this workspace",
            )

        # Validate db_type
        if not connector_factory.get(info.db_type):
            available = connector_factory.available_types()
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported db_type '{info.db_type}'. Available: {available}",
            )

        # Encrypt password
        encrypted_pwd = base64_encrypt(info.password)

        db_config = NL2SQLDbConfigModel(
            workspace_id=workspace_id,
            name=info.name,
            db_type=info.db_type,
            host=info.host,
            port=info.port,
            database_name=info.database_name,
            schema_name=info.schema_name,
            username=info.username,
            encrypted_password=encrypted_pwd,
            extra_params=info.extra_params,
            status=0,  # unverified
        )
        session.add(db_config)
        session.commit()
        session.refresh(db_config)

        TerraLogUtil.info(
            "db_config_created",
            config_id=db_config.id,
            workspace_id=workspace_id,
            db_type=info.db_type,
        )
        return DbConfigResponse.model_validate(db_config, from_attributes=True)

    @staticmethod
    async def update_db_config(
        *,
        session: Session,
        workspace_id: int,
        info: DbConfigUpdate,
    ) -> DbConfigResponse:
        """Update an existing database configuration."""
        db_config = session.get(NL2SQLDbConfigModel, info.id)
        if not db_config or db_config.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="DB config not found")

        update_data = info.model_dump(exclude_unset=True, exclude={"id"})

        if "name" in update_data and update_data["name"] != db_config.name:
            dup = session.exec(
                select(NL2SQLDbConfigModel).where(
                    NL2SQLDbConfigModel.workspace_id == workspace_id,
                    NL2SQLDbConfigModel.name == update_data["name"],
                )
            ).first()
            if dup:
                raise HTTPException(
                    status_code=400, detail="Name already taken")

        if "db_type" in update_data:
            if not connector_factory.get(update_data["db_type"]):
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported db_type '{update_data['db_type']}'",
                )

        # Handle password update
        if "password" in update_data and update_data["password"]:
            update_data["encrypted_password"] = base64_encrypt(
                update_data["password"])
        update_data.pop("password", None)

        # Reset status to unverified on connection-related changes
        conn_fields = {"host", "port", "database_name",
                       "username", "password", "db_type"}
        if conn_fields & update_data.keys():
            update_data["status"] = 0

        db_config.sqlmodel_update(update_data)
        session.add(db_config)
        session.commit()
        session.refresh(db_config)

        TerraLogUtil.info("db_config_updated", config_id=db_config.id)
        return DbConfigResponse.model_validate(db_config, from_attributes=True)

    @staticmethod
    async def delete_db_config(
        *,
        session: Session,
        workspace_id: int,
        config_id: int,
    ) -> Dict[str, Any]:
        """Delete a DB config (if not in use by any instance)."""
        db_config = session.get(NL2SQLDbConfigModel, config_id)
        if not db_config or db_config.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="DB config not found")

        # Check if any instance uses this config
        instance = session.exec(
            select(NL2SQLInstanceModel).where(
                NL2SQLInstanceModel.db_config_id == config_id
            )
        ).first()
        if instance:
            raise HTTPException(
                status_code=400,
                detail=f"DB config is in use by instance '{instance.name}'",
            )

        session.delete(db_config)
        session.commit()

        TerraLogUtil.info("db_config_deleted", config_id=config_id)
        return {"config_id": config_id, "deleted": True}

    @staticmethod
    async def get_db_config(
        *,
        session: Session,
        workspace_id: int,
        config_id: int,
    ) -> DbConfigResponse:
        """Get a single DB config."""
        db_config = session.get(NL2SQLDbConfigModel, config_id)
        if not db_config or db_config.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="DB config not found")
        return DbConfigResponse.model_validate(db_config, from_attributes=True)

    @staticmethod
    async def list_db_configs(
        *,
        session: Session,
        workspace_id: int,
        keyword: Optional[str] = None,
    ) -> List[DbConfigListItem]:
        """List DB configs in a workspace."""
        stmt = select(NL2SQLDbConfigModel).where(
            NL2SQLDbConfigModel.workspace_id == workspace_id
        )
        if keyword:
            stmt = stmt.where(NL2SQLDbConfigModel.name.ilike(f"%{keyword}%"))
        stmt = stmt.order_by(NL2SQLDbConfigModel.created_at.desc())

        configs = session.exec(stmt).all()
        return [DbConfigListItem.model_validate(c, from_attributes=True) for c in configs]

    @staticmethod
    async def test_db_connection(
        *,
        session: Session,
        workspace_id: int,
        info: DbConfigTestRequest,
    ) -> DbConfigTestResponse:
        """Test a database connection without persisting."""
        connector = connector_factory.get(info.db_type)
        if not connector:
            return DbConfigTestResponse(
                success=False,
                message=f"Unsupported db_type '{info.db_type}'",
            )

        # Connector.test_connection returns DbConfigTestResponse directly
        return connector.test_connection(
            host=info.host,
            port=info.port,
            database=info.database_name,
            username=info.username,
            password=info.password,
            schema=info.schema_name or "",
            extra_params=info.extra_params or "",
        )

    @staticmethod
    async def test_db_config_by_id(
        *,
        session: Session,
        workspace_id: int,
        config_id: int,
    ) -> DbConfigTestResponse:
        """Test a saved DB config by ID and update its status."""
        db_config = session.get(NL2SQLDbConfigModel, config_id)
        if not db_config or db_config.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="DB config not found")

        password = base64_decrypt(db_config.encrypted_password)
        connector = connector_factory.get(db_config.db_type)
        if not connector:
            db_config.status = 2
            session.add(db_config)
            session.commit()
            return DbConfigTestResponse(
                success=False,
                message=f"Unsupported db_type '{db_config.db_type}'",
            )

        # Connector.test_connection returns DbConfigTestResponse directly
        result = connector.test_connection(
            host=db_config.host,
            port=db_config.port,
            database=db_config.database_name,
            username=db_config.username,
            password=password,
            schema=db_config.schema_name or "",
            extra_params=db_config.extra_params or "",
        )

        # Update status based on result
        db_config.status = 1 if result.success else 2
        session.add(db_config)
        session.commit()

        return result

    # ====================== NL2SQL Instance CRUD ======================

    @staticmethod
    async def create_instance(
        *,
        session: Session,
        workspace_id: int,
        info: NL2SQLInstanceCreate,
    ) -> NL2SQLInstanceResponse:
        """Create a new NL2SQL instance.

        If info.table_names is provided, automatically syncs those tables
        after instance creation (two-step wizard flow).
        """
        existing = session.exec(
            select(NL2SQLInstanceModel).where(
                NL2SQLInstanceModel.workspace_id == workspace_id,
                NL2SQLInstanceModel.name == info.name,
            )
        ).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Instance '{info.name}' already exists in this workspace",
            )

        # Validate db_config_id
        db_config = session.get(NL2SQLDbConfigModel, info.db_config_id)
        if not db_config or db_config.workspace_id != workspace_id:
            raise HTTPException(status_code=400, detail="Invalid db_config_id")

        # Validate embedding_model_id if provided
        if info.embedding_model_id:
            model = session.get(AiModelDetail, info.embedding_model_id)
            if not model or model.llm_type != "embedding":
                raise HTTPException(
                    status_code=400, detail="Invalid embedding model ID")

        # Validate ddl_mode
        if info.ddl_mode not in ("full", "compact"):
            raise HTTPException(
                status_code=400, detail="ddl_mode must be 'full' or 'compact'")

        instance = NL2SQLInstanceModel(
            workspace_id=workspace_id,
            name=info.name,
            description=info.description,
            db_config_id=info.db_config_id,
            embedding_model_id=info.embedding_model_id,
            ddl_mode=info.ddl_mode,
            status=0,  # init
        )
        session.add(instance)
        session.commit()
        session.refresh(instance)

        # Resolve embedding dimension and create vector tables
        try:
            cap = await _resolve_embed_capability(session, instance)
            create_instance_tables(instance.id, cap.dimension)
            instance.status = 1  # ready
            session.add(instance)
            session.commit()
            session.refresh(instance)
        except Exception as e:
            TerraLogUtil.exception(
                "nl2sql_instance_table_creation_failed",
                instance_id=instance.id,
                error=str(e),
            )

        TerraLogUtil.info(
            "nl2sql_instance_created",
            instance_id=instance.id,
            workspace_id=workspace_id,
        )

        # Auto-sync selected tables if provided (wizard step 2)
        if info.table_names and instance.status == 1:
            try:
                await NL2SQLService.sync_schema(
                    session=session,
                    workspace_id=workspace_id,
                    instance_id=instance.id,
                    table_names=info.table_names,
                )
                session.refresh(instance)
            except Exception as e:
                TerraLogUtil.exception(
                    "nl2sql_instance_auto_sync_failed",
                    instance_id=instance.id,
                    error=str(e),
                )

        return NL2SQLInstanceResponse.model_validate(instance, from_attributes=True)

    @staticmethod
    async def update_instance(
        *,
        session: Session,
        workspace_id: int,
        info: NL2SQLInstanceUpdate,
    ) -> NL2SQLInstanceResponse:
        """Update an existing NL2SQL instance.

        If ddl_mode changes, regenerates all DDL embeddings with the
        new mode strategy.
        """
        instance = session.get(NL2SQLInstanceModel, info.id)
        if not instance or instance.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Instance not found")

        update_data = info.model_dump(exclude_unset=True, exclude={"id"})

        if "name" in update_data and update_data["name"] != instance.name:
            dup = session.exec(
                select(NL2SQLInstanceModel).where(
                    NL2SQLInstanceModel.workspace_id == workspace_id,
                    NL2SQLInstanceModel.name == update_data["name"],
                )
            ).first()
            if dup:
                raise HTTPException(
                    status_code=400, detail="Name already taken")

        if "embedding_model_id" in update_data and update_data["embedding_model_id"]:
            model = session.get(
                AiModelDetail, update_data["embedding_model_id"])
            if not model or model.llm_type != "embedding":
                raise HTTPException(
                    status_code=400, detail="Invalid embedding model ID")

        # Validate ddl_mode if provided
        if "ddl_mode" in update_data and update_data["ddl_mode"]:
            if update_data["ddl_mode"] not in ("full", "compact"):
                raise HTTPException(
                    status_code=400,
                    detail="ddl_mode must be 'full' or 'compact'",
                )

        # Detect ddl_mode change for re-embedding
        old_ddl_mode = instance.ddl_mode
        ddl_mode_changed = (
            "ddl_mode" in update_data
            and update_data["ddl_mode"] is not None
            and update_data["ddl_mode"] != old_ddl_mode
        )

        instance.sqlmodel_update(update_data)
        session.add(instance)
        session.commit()
        session.refresh(instance)

        # Re-generate all DDL embeddings when ddl_mode changes
        if ddl_mode_changed:
            try:
                tables = await NL2SQLService.get_schema_tables(
                    session=session,
                    workspace_id=workspace_id,
                    instance_id=instance.id,
                )
                if tables:
                    db_config = session.get(
                        NL2SQLDbConfigModel, instance.db_config_id)
                    db_type = db_config.db_type if db_config else ""
                    await _generate_ddl_training_data(
                        session=session,
                        instance=instance,
                        tables=tables,
                        db_type=db_type,
                    )
                    # Refresh ddl_count
                    instance.ddl_count = session.exec(
                        select(func.count(NL2SQLTrainingDataModel.id)).where(
                            NL2SQLTrainingDataModel.instance_id == instance.id,
                            NL2SQLTrainingDataModel.data_type == "ddl",
                        )
                    ).one()
                    session.add(instance)
                    session.commit()
                    session.refresh(instance)

                TerraLogUtil.info(
                    "nl2sql_ddl_mode_changed_regen",
                    instance_id=instance.id,
                    old_mode=old_ddl_mode,
                    new_mode=instance.ddl_mode,
                )
            except Exception as e:
                TerraLogUtil.exception(
                    "nl2sql_ddl_mode_regen_failed",
                    instance_id=instance.id,
                    error=str(e),
                )

        TerraLogUtil.info("nl2sql_instance_updated", instance_id=instance.id)
        return NL2SQLInstanceResponse.model_validate(instance, from_attributes=True)

    @staticmethod
    async def delete_instance(
        *,
        session: Session,
        workspace_id: int,
        instance_id: int,
    ) -> Dict[str, Any]:
        """Delete an NL2SQL instance and all associated data."""
        instance = session.get(NL2SQLInstanceModel, instance_id)
        if not instance or instance.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Instance not found")

        # Delete vector tables
        drop_instance_tables(instance_id)

        # Delete training data
        training_data = session.exec(
            select(NL2SQLTrainingDataModel).where(
                NL2SQLTrainingDataModel.instance_id == instance_id
            )
        ).all()
        for td in training_data:
            session.delete(td)

        # Delete schema meta
        schema_meta = session.exec(
            select(NL2SQLSchemaMetaModel).where(
                NL2SQLSchemaMetaModel.instance_id == instance_id
            )
        ).all()
        for sm in schema_meta:
            session.delete(sm)

        session.delete(instance)
        session.commit()

        TerraLogUtil.info(
            "nl2sql_instance_deleted",
            instance_id=instance_id,
            training_data_count=len(training_data),
        )
        return {
            "instance_id": instance_id,
            "deleted_training_data": len(training_data),
        }

    @staticmethod
    async def get_instance(
        *,
        session: Session,
        workspace_id: int,
        instance_id: int,
    ) -> NL2SQLInstanceResponse:
        """Get a single NL2SQL instance."""
        instance = session.get(NL2SQLInstanceModel, instance_id)
        if not instance or instance.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Instance not found")
        return NL2SQLInstanceResponse.model_validate(instance, from_attributes=True)

    @staticmethod
    async def list_instances(
        *,
        session: Session,
        workspace_id: int,
        keyword: Optional[str] = None,
    ) -> List[NL2SQLInstanceListItem]:
        """List NL2SQL instances in a workspace."""
        stmt = select(NL2SQLInstanceModel).where(
            NL2SQLInstanceModel.workspace_id == workspace_id
        )
        if keyword:
            stmt = stmt.where(NL2SQLInstanceModel.name.ilike(f"%{keyword}%"))
        stmt = stmt.order_by(NL2SQLInstanceModel.created_at.desc())

        instances = session.exec(stmt).all()
        return [NL2SQLInstanceListItem.model_validate(i, from_attributes=True) for i in instances]

    # ====================== Schema Sync ======================

    @staticmethod
    async def discover_tables(
        *,
        session: Session,
        workspace_id: int,
        instance_id: int,
    ) -> DiscoverTablesResponse:
        """Discover tables from the target database without fetching columns.

        Returns a lightweight list of table names with synced status.
        """
        instance = session.get(NL2SQLInstanceModel, instance_id)
        if not instance or instance.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Instance not found")

        db_config = session.get(NL2SQLDbConfigModel, instance.db_config_id)
        if not db_config:
            raise HTTPException(status_code=400, detail="DB config not found")

        connector = connector_factory.get(db_config.db_type)
        if not connector:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported db_type '{db_config.db_type}'",
            )

        password = base64_decrypt(db_config.encrypted_password)

        tables_raw = connector.get_tables(
            db_config.host,
            db_config.port,
            db_config.database_name,
            db_config.username,
            password,
            db_config.schema_name or "",
            db_config.extra_params or "",
        )

        # Get already-synced table names for this instance
        synced_rows = session.exec(
            select(NL2SQLSchemaMetaModel.table_name).where(
                NL2SQLSchemaMetaModel.instance_id == instance_id,
                NL2SQLSchemaMetaModel.column_name == None,  # noqa: E711
            )
        ).all()
        synced_set = set(synced_rows)

        items = [
            DiscoverTableItem(
                table_name=t["table_name"],
                table_comment=t.get("table_comment") or None,
                synced=t["table_name"] in synced_set,
            )
            for t in tables_raw
        ]

        TerraLogUtil.info(
            "nl2sql_tables_discovered",
            instance_id=instance_id,
            total=len(items),
            synced=len([i for i in items if i.synced]),
        )
        return DiscoverTablesResponse(
            instance_id=instance_id,
            tables=items,
            total=len(items),
        )

    @staticmethod
    async def sync_schema(
        *,
        session: Session,
        workspace_id: int,
        instance_id: int,
        table_names: Optional[List[str]] = None,
    ) -> SchemaSyncResponse:
        """Sync schema from database to instance and generate DDL training data.

        Args:
            table_names: If provided, only sync these tables (selective).
                         None = sync all tables (full replace).
        """
        instance = session.get(NL2SQLInstanceModel, instance_id)
        if not instance or instance.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Instance not found")

        db_config = session.get(NL2SQLDbConfigModel, instance.db_config_id)
        if not db_config:
            raise HTTPException(status_code=400, detail="DB config not found")

        connector = connector_factory.get(db_config.db_type)
        if not connector:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported db_type '{db_config.db_type}'",
            )

        password = base64_decrypt(db_config.encrypted_password)

        # Set instance to syncing
        instance.status = 2
        session.add(instance)
        session.commit()

        try:
            # Extract schema
            tables = extract_full_schema(
                connector=connector,
                host=db_config.host,
                port=db_config.port,
                database=db_config.database_name,
                username=db_config.username,
                password=password,
                schema=db_config.schema_name or "",
                extra_params=db_config.extra_params or "",
                table_names=table_names,
            )

            # Sync to schema_meta table
            sync_response = sync_schema_to_db(
                session=session,
                instance_id=instance_id,
                db_config_id=db_config.id,
                workspace_id=workspace_id,
                tables=tables,
                table_names=table_names,
            )

            # Generate DDL training data
            ddl_generated = await _generate_ddl_training_data(
                session=session,
                instance=instance,
                tables=tables,
                db_type=db_config.db_type,
                table_names=table_names,
            )
            sync_response.ddl_generated = ddl_generated

            # Update instance counts
            instance.ddl_count = session.exec(
                select(func.count(NL2SQLTrainingDataModel.id)).where(
                    NL2SQLTrainingDataModel.instance_id == instance_id,
                    NL2SQLTrainingDataModel.data_type == "ddl",
                )
            ).one()
            instance.status = 1  # ready
            session.add(instance)
            session.commit()

            TerraLogUtil.info(
                "nl2sql_schema_synced",
                instance_id=instance_id,
                tables=sync_response.tables_synced,
                ddl_generated=ddl_generated,
            )
            return sync_response

        except Exception as e:
            instance.status = 1  # back to ready (not syncing)
            session.add(instance)
            session.commit()
            TerraLogUtil.exception(
                "nl2sql_schema_sync_failed",
                instance_id=instance_id,
                error=str(e),
            )
            raise HTTPException(
                status_code=500, detail=f"Schema sync failed: {e}")

    @staticmethod
    async def get_schema_tables(
        *,
        session: Session,
        workspace_id: int,
        instance_id: int,
    ) -> List[SchemaTableInfo]:
        """Get synced schema tables for an instance."""
        instance = session.get(NL2SQLInstanceModel, instance_id)
        if not instance or instance.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Instance not found")

        # Get table-level rows (column_name IS NULL)
        table_rows = session.exec(
            select(NL2SQLSchemaMetaModel).where(
                NL2SQLSchemaMetaModel.instance_id == instance_id,
                NL2SQLSchemaMetaModel.column_name == None,  # noqa: E711
            )
        ).all()

        result = []
        for tr in table_rows:
            # Get columns for this table
            col_rows = session.exec(
                select(NL2SQLSchemaMetaModel).where(
                    NL2SQLSchemaMetaModel.instance_id == instance_id,
                    NL2SQLSchemaMetaModel.table_name == tr.table_name,
                    NL2SQLSchemaMetaModel.column_name != None,  # noqa: E711
                )
            ).all()

            columns = [
                SchemaColumnInfo(
                    column_name=cr.column_name,
                    column_type=cr.column_type,
                    column_comment=cr.column_comment,
                    is_primary_key=cr.is_primary_key,
                    is_nullable=cr.is_nullable,
                )
                for cr in col_rows
            ]

            result.append(SchemaTableInfo(
                table_schema=tr.table_schema,
                table_name=tr.table_name,
                table_comment=tr.table_comment,
                columns=columns,
            ))

        return result

    # ====================== Schema Table Operations ======================

    @staticmethod
    async def update_schema_table(
        *,
        session: Session,
        workspace_id: int,
        instance_id: int,
        table_name: str,
        info: UpdateSchemaTableRequest,
    ) -> SchemaTableInfo:
        """Update a schema table's description and columns.

        - Updates table_comment on the table-level row.
        - Updates column_comment on listed columns.
        - Deletes column rows not present in info.columns.
        - Regenerates DDL training data + vector for this table.
        """
        instance = session.get(NL2SQLInstanceModel, instance_id)
        if not instance or instance.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Instance not found")

        # Get table-level row
        table_row = session.exec(
            select(NL2SQLSchemaMetaModel).where(
                NL2SQLSchemaMetaModel.instance_id == instance_id,
                NL2SQLSchemaMetaModel.table_name == table_name,
                NL2SQLSchemaMetaModel.column_name == None,  # noqa: E711
            )
        ).first()
        if not table_row:
            raise HTTPException(
                status_code=404, detail=f"Table '{table_name}' not found")

        # Update table comment
        table_row.table_comment = info.table_comment
        session.add(table_row)

        # Build map of columns to keep
        keep_columns = {c.column_name: c for c in info.columns}

        # Get all existing column rows
        col_rows = session.exec(
            select(NL2SQLSchemaMetaModel).where(
                NL2SQLSchemaMetaModel.instance_id == instance_id,
                NL2SQLSchemaMetaModel.table_name == table_name,
                NL2SQLSchemaMetaModel.column_name != None,  # noqa: E711
            )
        ).all()

        for cr in col_rows:
            if cr.column_name in keep_columns:
                # Update comment
                cr.column_comment = keep_columns[cr.column_name].column_comment
                session.add(cr)
            else:
                # Delete column not in the keep list
                session.delete(cr)

        session.flush()

        # Rebuild SchemaTableInfo from updated data
        remaining_cols = session.exec(
            select(NL2SQLSchemaMetaModel).where(
                NL2SQLSchemaMetaModel.instance_id == instance_id,
                NL2SQLSchemaMetaModel.table_name == table_name,
                NL2SQLSchemaMetaModel.column_name != None,  # noqa: E711
            )
        ).all()

        updated_table = SchemaTableInfo(
            table_schema=table_row.table_schema,
            table_name=table_row.table_name,
            table_comment=table_row.table_comment,
            columns=[
                SchemaColumnInfo(
                    column_name=c.column_name,
                    column_type=c.column_type,
                    column_comment=c.column_comment,
                    is_primary_key=c.is_primary_key,
                    is_nullable=c.is_nullable,
                )
                for c in remaining_cols
            ],
        )

        # Regenerate DDL for this table
        db_config = session.get(NL2SQLDbConfigModel, instance.db_config_id)
        db_type = db_config.db_type if db_config else ""
        await _generate_ddl_training_data(
            session=session,
            instance=instance,
            tables=[updated_table],
            db_type=db_type,
            table_names=[table_name],
        )

        # Refresh ddl_count
        instance.ddl_count = session.exec(
            select(func.count(NL2SQLTrainingDataModel.id)).where(
                NL2SQLTrainingDataModel.instance_id == instance_id,
                NL2SQLTrainingDataModel.data_type == "ddl",
            )
        ).one()
        session.add(instance)
        session.commit()

        TerraLogUtil.info(
            "nl2sql_schema_table_updated",
            instance_id=instance_id,
            table_name=table_name,
            columns_kept=len(remaining_cols),
        )
        return updated_table

    @staticmethod
    async def delete_schema_table(
        *,
        session: Session,
        workspace_id: int,
        instance_id: int,
        table_name: str,
    ) -> DeleteSchemaTableResponse:
        """Delete a schema table and cascade cleanup.

        Deletes: schema_meta rows, DDL training_data, DDL vector.
        Updates: instance.ddl_count.
        """
        instance = session.get(NL2SQLInstanceModel, instance_id)
        if not instance or instance.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Instance not found")

        # Delete all schema_meta rows for this table
        meta_rows = session.exec(
            select(NL2SQLSchemaMetaModel).where(
                NL2SQLSchemaMetaModel.instance_id == instance_id,
                NL2SQLSchemaMetaModel.table_name == table_name,
            )
        ).all()
        schema_rows_deleted = len(meta_rows)
        for row in meta_rows:
            session.delete(row)

        # Delete DDL training data and its vector
        ddl_rows = session.exec(
            select(NL2SQLTrainingDataModel).where(
                NL2SQLTrainingDataModel.instance_id == instance_id,
                NL2SQLTrainingDataModel.data_type == "ddl",
                NL2SQLTrainingDataModel.table_name == table_name,
            )
        ).all()
        training_data_deleted = len(ddl_rows)
        vectors_deleted = 0
        for td in ddl_rows:
            delete_vector_by_training_data_id(
                instance_id, VECTOR_TYPE_DDL, td.id)
            vectors_deleted += 1
            session.delete(td)

        # Update instance ddl_count
        session.flush()
        instance.ddl_count = session.exec(
            select(func.count(NL2SQLTrainingDataModel.id)).where(
                NL2SQLTrainingDataModel.instance_id == instance_id,
                NL2SQLTrainingDataModel.data_type == "ddl",
            )
        ).one()
        session.add(instance)
        session.commit()

        TerraLogUtil.info(
            "nl2sql_schema_table_deleted",
            instance_id=instance_id,
            table_name=table_name,
            schema_rows=schema_rows_deleted,
            training_data=training_data_deleted,
        )
        return DeleteSchemaTableResponse(
            table_name=table_name,
            schema_rows_deleted=schema_rows_deleted,
            training_data_deleted=training_data_deleted,
            vectors_deleted=vectors_deleted,
        )

    @staticmethod
    async def discover_tables_by_config(
        *,
        session: Session,
        workspace_id: int,
        config_id: int,
    ) -> List[DiscoverTableItem]:
        """Discover tables from a DB config (before instance exists).

        Used during instance creation wizard step 2.
        """
        db_config = session.get(NL2SQLDbConfigModel, config_id)
        if not db_config or db_config.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="DB config not found")

        connector = connector_factory.get(db_config.db_type)
        if not connector:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported db_type '{db_config.db_type}'",
            )

        password = base64_decrypt(db_config.encrypted_password)

        tables_raw = connector.get_tables(
            db_config.host,
            db_config.port,
            db_config.database_name,
            db_config.username,
            password,
            db_config.schema_name or "",
            db_config.extra_params or "",
        )

        items = [
            DiscoverTableItem(
                table_name=t["table_name"],
                table_comment=t.get("table_comment") or None,
                synced=False,
            )
            for t in tables_raw
        ]

        TerraLogUtil.info(
            "nl2sql_tables_discovered_by_config",
            config_id=config_id,
            total=len(items),
        )
        return items

    # ====================== Training Data Management ======================

    @staticmethod
    async def add_ddl(
        *,
        session: Session,
        workspace_id: int,
        instance_id: int,
        info: AddDDLRequest,
    ) -> TrainingDataResponse:
        """Add a DDL training data entry."""
        instance = session.get(NL2SQLInstanceModel, instance_id)
        if not instance or instance.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Instance not found")

        td = NL2SQLTrainingDataModel(
            instance_id=instance_id,
            workspace_id=workspace_id,
            data_type="ddl",
            content=info.content,
            table_name=info.table_name,
            source="manual",
            status=0,  # pending_embed
        )
        session.add(td)
        session.commit()
        session.refresh(td)

        # Embed and store vector
        try:
            await _embed_training_data(session, instance, td)
        except Exception as e:
            TerraLogUtil.exception(
                "ddl_embedding_failed",
                training_data_id=td.id,
                error=str(e),
            )

        # Update instance count
        instance.ddl_count = session.exec(
            select(func.count(NL2SQLTrainingDataModel.id)).where(
                NL2SQLTrainingDataModel.instance_id == instance_id,
                NL2SQLTrainingDataModel.data_type == "ddl",
            )
        ).one()
        session.add(instance)
        session.commit()

        return TrainingDataResponse.model_validate(td, from_attributes=True)

    @staticmethod
    async def add_question_sql(
        *,
        session: Session,
        workspace_id: int,
        instance_id: int,
        info: AddQuestionSQLRequest,
    ) -> TrainingDataResponse:
        """Add a question-SQL pair training data entry."""
        instance = session.get(NL2SQLInstanceModel, instance_id)
        if not instance or instance.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Instance not found")

        # Content is the question for embedding
        td = NL2SQLTrainingDataModel(
            instance_id=instance_id,
            workspace_id=workspace_id,
            data_type="sql",
            content=info.question,  # question is the primary content
            question=info.question,
            sql_text=info.sql_text,
            source="manual",
            status=0,
        )
        session.add(td)
        session.commit()
        session.refresh(td)

        # Embed and store vector
        try:
            await _embed_training_data(session, instance, td)
        except Exception as e:
            TerraLogUtil.exception(
                "sql_embedding_failed",
                training_data_id=td.id,
                error=str(e),
            )

        # Update instance count
        instance.sql_count = session.exec(
            select(func.count(NL2SQLTrainingDataModel.id)).where(
                NL2SQLTrainingDataModel.instance_id == instance_id,
                NL2SQLTrainingDataModel.data_type == "sql",
            )
        ).one()
        session.add(instance)
        session.commit()

        return TrainingDataResponse.model_validate(td, from_attributes=True)

    @staticmethod
    async def add_documentation(
        *,
        session: Session,
        workspace_id: int,
        instance_id: int,
        info: AddDocumentationRequest,
    ) -> TrainingDataResponse:
        """Add a documentation/glossary training data entry."""
        instance = session.get(NL2SQLInstanceModel, instance_id)
        if not instance or instance.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Instance not found")

        td = NL2SQLTrainingDataModel(
            instance_id=instance_id,
            workspace_id=workspace_id,
            data_type="doc",
            content=info.content,
            source="manual",
            status=0,
        )
        session.add(td)
        session.commit()
        session.refresh(td)

        # Embed and store vector
        try:
            await _embed_training_data(session, instance, td)
        except Exception as e:
            TerraLogUtil.exception(
                "doc_embedding_failed",
                training_data_id=td.id,
                error=str(e),
            )

        # Update instance count
        instance.doc_count = session.exec(
            select(func.count(NL2SQLTrainingDataModel.id)).where(
                NL2SQLTrainingDataModel.instance_id == instance_id,
                NL2SQLTrainingDataModel.data_type == "doc",
            )
        ).one()
        session.add(instance)
        session.commit()

        return TrainingDataResponse.model_validate(td, from_attributes=True)

    @staticmethod
    async def delete_training_data(
        *,
        session: Session,
        workspace_id: int,
        instance_id: int,
        training_data_id: int,
    ) -> Dict[str, Any]:
        """Delete a training data entry and its vector."""
        td = session.get(NL2SQLTrainingDataModel, training_data_id)
        if not td or td.instance_id != instance_id or td.workspace_id != workspace_id:
            raise HTTPException(
                status_code=404, detail="Training data not found")

        # Delete vector
        vector_type = _data_type_to_vector_type(td.data_type)
        delete_vector_by_training_data_id(
            instance_id, vector_type, training_data_id)

        data_type = td.data_type
        session.delete(td)

        # Update instance count
        instance = session.get(NL2SQLInstanceModel, instance_id)
        if instance:
            if data_type == "ddl":
                instance.ddl_count = max(0, instance.ddl_count - 1)
            elif data_type == "sql":
                instance.sql_count = max(0, instance.sql_count - 1)
            else:
                instance.doc_count = max(0, instance.doc_count - 1)
            session.add(instance)

        session.commit()

        TerraLogUtil.info(
            "training_data_deleted",
            training_data_id=training_data_id,
            data_type=data_type,
        )
        return {"training_data_id": training_data_id, "deleted": True}

    @staticmethod
    async def list_training_data(
        *,
        session: Session,
        workspace_id: int,
        instance_id: int,
        data_type: Optional[str] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[List[TrainingDataListItem], int]:
        """List training data for an instance with pagination."""
        instance = session.get(NL2SQLInstanceModel, instance_id)
        if not instance or instance.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Instance not found")

        stmt = select(NL2SQLTrainingDataModel).where(
            NL2SQLTrainingDataModel.instance_id == instance_id
        )
        if data_type:
            stmt = stmt.where(NL2SQLTrainingDataModel.data_type == data_type)

        # Count
        count_stmt = select(func.count(NL2SQLTrainingDataModel.id)).where(
            NL2SQLTrainingDataModel.instance_id == instance_id
        )
        if data_type:
            count_stmt = count_stmt.where(
                NL2SQLTrainingDataModel.data_type == data_type)
        total = session.exec(count_stmt).one()

        # Paginate
        stmt = stmt.order_by(NL2SQLTrainingDataModel.created_at.desc())
        stmt = stmt.offset(offset).limit(limit)

        items = session.exec(stmt).all()
        return [TrainingDataListItem.model_validate(i, from_attributes=True) for i in items], total

    # ====================== Search ======================

    @staticmethod
    async def search(
        *,
        session: Session,
        workspace_id: int,
        request: NL2SQLSearchRequest,
    ) -> NL2SQLSearchResponse:
        """Execute NL2SQL similarity search across DDL, SQL, and documentation."""
        instance = session.get(NL2SQLInstanceModel, request.instance_id)
        if not instance or instance.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Instance not found")

        if not instance_tables_exist(request.instance_id):
            raise HTTPException(
                status_code=400,
                detail="Instance vector tables not ready. Try syncing schema first.",
            )

        # Resolve embedding
        cap = await _resolve_embed_capability(session, instance)

        # Embed query
        query_embedding = cap.model.get_query_embedding(request.question)

        # Default top_k values
        top_k_ddl = request.top_k_ddl or settings.NL2SQL_DEFAULT_TOP_K_DDL
        top_k_sql = request.top_k_sql or settings.NL2SQL_DEFAULT_TOP_K_SQL
        top_k_doc = request.top_k_doc or settings.NL2SQL_DEFAULT_TOP_K_DOC

        # Search DDL
        ddl_results = search_similar(
            instance_id=request.instance_id,
            vector_type=VECTOR_TYPE_DDL,
            query_embedding=query_embedding,
            top_k=top_k_ddl,
        )

        # Search SQL
        sql_results = search_similar(
            instance_id=request.instance_id,
            vector_type=VECTOR_TYPE_SQL,
            query_embedding=query_embedding,
            top_k=top_k_sql,
        )

        # Search DOC
        doc_results = search_similar(
            instance_id=request.instance_id,
            vector_type=VECTOR_TYPE_DOC,
            query_embedding=query_embedding,
            top_k=top_k_doc,
        )

        # Build response with full training data
        similar_sqls = []
        for td_id, content, score in sql_results:
            td = session.get(NL2SQLTrainingDataModel, td_id)
            if td:
                similar_sqls.append(SimilarSQLResult(
                    id=td.id,
                    question=td.question or td.content,
                    sql_text=td.sql_text or "",
                    score=round(score, 4),
                ))

        related_ddls = []
        for td_id, content, score in ddl_results:
            td = session.get(NL2SQLTrainingDataModel, td_id)
            if td:
                related_ddls.append(RelatedDDLResult(
                    id=td.id,
                    content=td.content,
                    table_name=td.table_name,
                    score=round(score, 4),
                ))

        related_docs = []
        for td_id, content, score in doc_results:
            td = session.get(NL2SQLTrainingDataModel, td_id)
            if td:
                related_docs.append(RelatedDocResult(
                    id=td.id,
                    content=td.content,
                    score=round(score, 4),
                ))

        TerraLogUtil.info(
            "nl2sql_search_completed",
            instance_id=request.instance_id,
            ddl_count=len(related_ddls),
            sql_count=len(similar_sqls),
            doc_count=len(related_docs),
        )

        return NL2SQLSearchResponse(
            question=request.question,
            similar_sqls=similar_sqls,
            related_ddls=related_ddls,
            related_docs=related_docs,
        )


# ====================== Internal helpers ======================


def _data_type_to_vector_type(data_type: str) -> str:
    """Map training data type to vector type."""
    mapping = {
        "ddl": VECTOR_TYPE_DDL,
        "sql": VECTOR_TYPE_SQL,
        "doc": VECTOR_TYPE_DOC,
    }
    return mapping.get(data_type, VECTOR_TYPE_DOC)


async def _resolve_embed_capability(
    session: Session,
    instance: NL2SQLInstanceModel,
) -> EmbeddingModelCapability:
    """Resolve embedding model capability for an NL2SQL instance."""
    model_id = instance.embedding_model_id

    if model_id:
        db_model = session.get(AiModelDetail, model_id)
    else:
        db_model = session.exec(
            select(AiModelDetail).where(
                AiModelDetail.llm_type == "embedding",
                AiModelDetail.status == 1,
            ).order_by(AiModelDetail.created_at.desc())
        ).first()

    if not db_model:
        raise HTTPException(
            status_code=500,
            detail="No embedding model configured. Add one in system settings.",
        )

    api_key = db_model.api_key or ""
    api_domain = db_model.api_domain or ""
    try:
        if api_domain and not api_domain.startswith("http"):
            api_domain = base64_decrypt(api_domain)
        if api_key and not api_key.startswith("sk-"):
            api_key = base64_decrypt(api_key)
    except Exception:
        pass

    # Parse config for dimension and batch_size
    config_dimension = None
    config_batch_size = None
    if db_model.config:
        try:
            for item in json.loads(db_model.config):
                if item.get("key") == "dimension":
                    config_dimension = int(item["val"])
                elif item.get("key") == "batch_size":
                    config_batch_size = int(item["val"])
        except (json.JSONDecodeError, ValueError, KeyError):
            pass

    # Check cache
    cached = EmbeddingProviderRegistry.get_capability(db_model.id)
    if cached:
        return cached

    embed_model = EmbeddingProviderRegistry.get(
        model_id=db_model.id,
        model_name=db_model.base_model,
        api_key=api_key,
        api_base=api_domain,
        dimension=config_dimension,
    )

    batch_size = config_batch_size or DEFAULT_SAFE_BATCH_SIZE
    dimension = config_dimension or settings.RAG_EMBEDDING_DIMENSION

    cap = EmbeddingModelCapability(
        model=embed_model,
        dimension=dimension,
        batch_size=batch_size,
    )

    # Probe dimension if not cached
    try:
        probed_dim = await probe_embedding_dimension(embed_model)
        cap.dimension = probed_dim
    except Exception:
        pass

    EmbeddingProviderRegistry.set_capability(db_model.id, cap)
    return cap


async def _embed_training_data(
    session: Session,
    instance: NL2SQLInstanceModel,
    td: NL2SQLTrainingDataModel,
) -> None:
    """Embed a training data entry and store its vector."""
    cap = await _resolve_embed_capability(session, instance)

    # Get embedding
    embedding = cap.model.get_text_embedding(td.content)

    # Store vector
    vector_type = _data_type_to_vector_type(td.data_type)
    add_vector(
        instance_id=instance.id,
        vector_type=vector_type,
        training_data_id=td.id,
        content=td.content,
        embedding=embedding,
    )

    # Update status
    td.status = 1  # embedded
    session.add(td)
    session.commit()


async def _generate_ddl_training_data(
    session: Session,
    instance: NL2SQLInstanceModel,
    tables: List[SchemaTableInfo],
    db_type: str,
    table_names: Optional[List[str]] = None,
) -> int:
    """Generate DDL training data from extracted schema tables.

    When table_names is None, replaces all auto_sync DDL entries.
    When table_names is provided, only replaces DDL entries for those tables.

    DDL mode branching:
      - full:    embedding text = full M-Schema DDL
      - compact: embedding text = "{table_name}: {table_comment}"
    In both modes, training_data.content stores the full M-Schema DDL.
    """
    # Build base query for existing auto_sync DDL entries
    stmt = select(NL2SQLTrainingDataModel).where(
        NL2SQLTrainingDataModel.instance_id == instance.id,
        NL2SQLTrainingDataModel.data_type == "ddl",
        NL2SQLTrainingDataModel.source == "auto_sync",
    )
    if table_names is not None:
        stmt = stmt.where(
            NL2SQLTrainingDataModel.table_name.in_(set(table_names)))

    existing = session.exec(stmt).all()

    for ex in existing:
        delete_vector_by_training_data_id(
            instance.id, VECTOR_TYPE_DDL, ex.id)
        session.delete(ex)
    session.flush()

    # Resolve embedding capability
    cap = await _resolve_embed_capability(session, instance)

    ddl_mode = getattr(instance, "ddl_mode", "full") or "full"

    # Create new DDL entries
    created = 0
    batch_items = []

    for table in tables:
        ddl_text = generate_ddl_text(table, db_type)

        # Determine embedding text based on mode
        if ddl_mode == "compact":
            embed_text = build_compact_embedding_text(table)
        else:
            embed_text = ddl_text

        td = NL2SQLTrainingDataModel(
            instance_id=instance.id,
            workspace_id=instance.workspace_id,
            data_type="ddl",
            content=ddl_text,
            table_name=table.table_name,
            source="auto_sync",
            status=0,
        )
        session.add(td)
        session.flush()  # Get ID

        # Prepare for batch embedding
        embedding = cap.model.get_text_embedding(embed_text)
        batch_items.append((td.id, ddl_text, embedding))

        td.status = 1  # embedded
        session.add(td)
        created += 1

    # Batch add vectors
    if batch_items:
        add_vectors_batch(instance.id, VECTOR_TYPE_DDL, batch_items)

    session.commit()
    return created
