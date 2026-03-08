import json
from typing import Any, Dict, List, Optional

from pydantic.types import T
from sqlmodel import Session, func, select, update
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse

from app.models.ai_model import AiModelDetail
from app.models.mcp_server import MCPServerModel, McpTransportType
from app.models.user import UserModel
from app.schemas.ai_model import AiModelCreator, AiModelEditor, AiModelConfigItem, AiModelGridItem, AiModelItem
from app.schemas.mcp_server import (
    MCPServerCreate,
    MCPServerUpdate,
    MCPServerResponse,
    MCPServerGridItem,
    ToolInfo,
    ToolCallResponse,
)
from app.core.common.crypt import base64_decrypt, base64_encrypt
from app.core.common.logging import TerraLogUtil
from app.core.mcp.standard import StandardMCPClient
from app.core.mcp.utils import get_tools_info, invoke_tool_with_timeout


class SystemService:

    @staticmethod
    async def get_default_llm_config(*, session: Session):
        db_model = session.exec(
            select(AiModelDetail).where(AiModelDetail.default_model == True)
        ).first()
        if not db_model:
            raise HTTPException(
                status_code=404, detail="No default LLM model found")
        return db_model

    @staticmethod
    async def get_backup_llm_config(*, session: Session):
        db_model = session.exec(
            select(AiModelDetail).where(AiModelDetail.backup_model == True)
        ).first()
        if not db_model:
            raise HTTPException(
                status_code=404, detail="No backup LLM model found")
        return db_model

    @staticmethod
    async def create_ai_model(*, session: Session, info: AiModelCreator, current_user: UserModel):
        data = info.model_dump(exclude_unset=True)
        data["config"] = json.dumps(
            [item.model_dump(exclude_unset=True) for item in info.config_list])
        data.pop("config_list", None)
        detail = AiModelDetail.model_validate(data)

        count = session.exec(select(func.count(AiModelDetail.id))).one()
        if count == 0:
            detail.default_model = True
        session.add(detail)
        session.commit()
        session.refresh(detail)
        return detail

    @staticmethod
    async def update_ai_model(*, session: Session, editor: AiModelEditor, current_user: UserModel):
        id = int(editor.id)
        data = editor.model_dump(exclude_unset=True)
        data["config"] = json.dumps(
            [item.model_dump(exclude_unset=True) for item in editor.config_list])
        data.pop("config_list", None)
        db_model = session.get(AiModelDetail, id)
        # update_data = AiModelDetail.model_validate(data)
        db_model.sqlmodel_update(data)
        session.add(db_model)
        session.commit()
        session.refresh(db_model)
        return db_model

    @staticmethod
    async def delete_ai_model(*, session: Session, id: int, current_user: UserModel):
        item = session.get(AiModelDetail, id)
        if not item:
            return JSONResponse(content={"id": id, "message": "AI model not found"}, status_code=404)
        if item.default_model or item.backup_model:
            return JSONResponse(content={"id": id, "message": "Cannot delete default or backup AI model"}, status_code=400)
        session.commit()
        return JSONResponse(content={"id": id, "message": "AI model deleted successfully"}, status_code=200)

    @staticmethod
    async def set_default_llm(*, session: Session, id: int, current_user: UserModel):
        db_model = session.get(AiModelDetail, id)
        if not db_model:
            return JSONResponse(content={"id": id, "message": "AI model not found"}, status_code=404)
        if db_model.default_model:
            return JSONResponse(content={"id": id, "message": "AI model is already the default model"}, status_code=200)

        try:
            session.exec(
                update(AiModelDetail).values(default_model=False)
            )
            db_model.default_model = True
            session.add(db_model)
            session.commit()
            return JSONResponse(content={"id": id, "message": "AI model set as default successfully"}, status_code=200)
        except Exception as e:
            session.rollback()
            return JSONResponse(content={"id": id, "message": "Failed to set AI model as default"}, status_code=500)

    @staticmethod
    async def set_backup_llm(*, session: Session, id: int, current_user: UserModel):
        db_model = session.get(AiModelDetail, id)
        if not db_model:
            return JSONResponse(content={"id": id, "message": "AI model not found"}, status_code=404)
        if db_model.backup_model:
            return JSONResponse(content={"id": id, "message": "AI model is already the backup model"}, status_code=200)

        try:
            session.exec(
                update(AiModelDetail).values(backup_model=False)
            )
            db_model.backup_model = True
            session.add(db_model)
            session.commit()
            return JSONResponse(content={"id": id, "message": "AI model set as backup successfully"}, status_code=200)
        except Exception as e:
            session.rollback()
            return JSONResponse(content={"id": id, "message": "Failed to set AI model as backup"}, status_code=500)

    @staticmethod
    async def get_ai_model_list(*, session: Session, keyword: str):
        statement = select(
            AiModelDetail.id,
            AiModelDetail.name,
            AiModelDetail.base_model,
            AiModelDetail.supplier,
            AiModelDetail.protocol,
            AiModelDetail.default_model,
            AiModelDetail.llm_type,
            AiModelDetail.backup_model
        )
        if keyword is not None:
            statement = statement.where(
                AiModelDetail.name.like(f"%{keyword}%"))
        statement = statement.order_by(AiModelDetail.default_model.desc(
        ), AiModelDetail.name, AiModelDetail.created_at)
        items = session.exec(statement).all()
        # Convert tuples to dictionaries
        return [
            {
                "id": item[0],
                "name": item[1],
                "base_model": item[2],
                "supplier": item[3],
                "protocol": item[4],
                "default_model": item[5],
                "llm_type": item[6],
                "backup_model": item[7]
            }
            for item in items
        ]

    @staticmethod
    async def get_model_by_id(*, session: Session, id: int):
        db_model = session.get(AiModelDetail, id)
        if not db_model:
            raise ValueError(f"AiModelDetail with id {id} not found")

        config_list: List[AiModelConfigItem] = []
        if db_model.config:
            try:
                raw = json.loads(db_model.config)
                config_list = [AiModelConfigItem(**item) for item in raw]
            except Exception:
                pass
        try:
            if db_model.api_key:
                db_model.api_key = base64_decrypt(db_model.api_key)
            if db_model.api_domain:
                db_model.api_domain = base64_decrypt(db_model.api_domain)
        except Exception:
            pass
        data = AiModelDetail.model_validate(
            db_model).model_dump(exclude_unset=True)
        data.pop("config", None)
        data["config_list"] = config_list
        return AiModelEditor(**data)

    # ==================== MCP Server Methods ====================

    @staticmethod
    async def create_mcp_server(
        *, session: Session, info: MCPServerCreate, current_user: UserModel
    ) -> MCPServerResponse:
        """Create a new MCP server configuration."""
        # Validate transport type
        valid_transports = [t.value for t in McpTransportType]
        if info.transport not in valid_transports:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid transport type. Must be one of: {valid_transports}",
            )

        data = info.model_dump(exclude_unset=True)
        # Map url to mcp_url
        data["mcp_url"] = data.pop("url")
        # Serialize config to JSON string
        if data.get("config"):
            data["config"] = json.dumps(data["config"])

        mcp_server = MCPServerModel.model_validate(data)
        session.add(mcp_server)
        session.commit()
        session.refresh(mcp_server)

        TerraLogUtil.info(
            "mcp_server_created",
            server_id=mcp_server.id,
            server_name=mcp_server.name,
            user_id=current_user.get("id") if isinstance(
                current_user, dict) else current_user.id,
        )
        return SystemService._to_mcp_server_response(mcp_server)

    @staticmethod
    async def get_mcp_server_by_id(
        *, session: Session, server_id: int
    ) -> MCPServerResponse:
        """Get MCP server by ID."""
        mcp_server = session.get(MCPServerModel, server_id)
        if not mcp_server:
            raise HTTPException(
                status_code=404, detail=f"MCP server with id {server_id} not found"
            )
        return SystemService._to_mcp_server_response(mcp_server)

    @staticmethod
    async def get_mcp_servers(*, session: Session) -> List[MCPServerGridItem]:
        """Get all MCP servers."""
        statement = select(MCPServerModel).order_by(
            MCPServerModel.created_at.desc())
        servers = session.exec(statement).all()
        return [
            MCPServerGridItem(
                id=s.id,
                name=s.name,
                url=s.mcp_url,
                transport=s.transport,
                created_at=s.created_at,
            )
            for s in servers
        ]

    @staticmethod
    async def update_mcp_server(
        *, session: Session, info: MCPServerUpdate, current_user: UserModel
    ) -> MCPServerResponse:
        """Update an existing MCP server configuration."""
        mcp_server = session.get(MCPServerModel, info.id)
        if not mcp_server:
            raise HTTPException(
                status_code=404, detail=f"MCP server with id {info.id} not found"
            )

        data = info.model_dump(exclude_unset=True)
        data.pop("id", None)

        # Map url to mcp_url
        if "url" in data:
            data["mcp_url"] = data.pop("url")

        # Validate transport type if provided
        if "transport" in data:
            valid_transports = [t.value for t in McpTransportType]
            if data["transport"] not in valid_transports:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid transport type. Must be one of: {valid_transports}",
                )

        # Serialize config to JSON string
        if data.get("config"):
            data["config"] = json.dumps(data["config"])

        mcp_server.sqlmodel_update(data)
        session.add(mcp_server)
        session.commit()
        session.refresh(mcp_server)

        TerraLogUtil.info(
            "mcp_server_updated",
            server_id=mcp_server.id,
            server_name=mcp_server.name,
            user_id=current_user.get("id") if isinstance(
                current_user, dict) else current_user.id,
        )
        return SystemService._to_mcp_server_response(mcp_server)

    @staticmethod
    async def delete_mcp_server(
        *, session: Session, server_id: int, current_user: UserModel
    ) -> MCPServerResponse:
        """Delete an MCP server configuration."""
        mcp_server = session.get(MCPServerModel, server_id)
        if not mcp_server:
            raise HTTPException(
                status_code=404, detail=f"MCP server with id {server_id} not found"
            )

        response = SystemService._to_mcp_server_response(mcp_server)
        session.delete(mcp_server)
        session.commit()

        TerraLogUtil.info(
            "mcp_server_deleted",
            server_id=server_id,
            user_id=current_user.get("id") if isinstance(
                current_user, dict) else current_user.id,
        )
        return response

    @staticmethod
    async def get_mcp_server_tools(
        *, session: Session, server_id: int
    ) -> List[ToolInfo]:
        """Get available tools from an MCP server."""
        mcp_server = session.get(MCPServerModel, server_id)
        if not mcp_server:
            raise HTTPException(
                status_code=404, detail=f"MCP server with id {server_id} not found"
            )

        server_configs = SystemService._build_server_config(mcp_server)
        client = StandardMCPClient()

        try:
            tools = await client.get_tools(server_configs)
            tools_info = get_tools_info(tools)
            return [
                ToolInfo(
                    name=t["name"],
                    description=t.get("description", ""),
                    args_schema=t.get("args_schema"),
                )
                for t in tools_info
            ]
        except Exception as e:
            TerraLogUtil.exception(
                "mcp_server_get_tools_failed",
                server_id=server_id,
                error=str(e),
            )
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get tools from MCP server: {str(e)}",
            )

    @staticmethod
    async def call_mcp_server_tool(
        *,
        session: Session,
        server_id: int,
        tool_name: str,
        arguments: Dict[str, Any],
        timeout: int = 10,
        retries: int = 2,
    ) -> ToolCallResponse:
        """Call a tool on an MCP server."""
        mcp_server = session.get(MCPServerModel, server_id)
        if not mcp_server:
            raise HTTPException(
                status_code=404, detail=f"MCP server with id {server_id} not found"
            )

        server_configs = SystemService._build_server_config(mcp_server)
        client = StandardMCPClient()

        try:
            result = await client.call_tool(
                server_configs,
                tool_name,
                arguments,
                timeout=timeout,
                retries=retries,
            )
            return ToolCallResponse(
                ok=True,
                result=result,
                error=None,
                elapsed_ms=None,
            )
        except RuntimeError as e:
            TerraLogUtil.exception(
                "mcp_server_tool_call_failed",
                server_id=server_id,
                tool_name=tool_name,
                error=str(e),
            )
            return ToolCallResponse(
                ok=False,
                result=None,
                error=str(e),
                elapsed_ms=None,
            )
        except Exception as e:
            TerraLogUtil.exception(
                "mcp_server_tool_call_error",
                server_id=server_id,
                tool_name=tool_name,
                error=str(e),
            )
            raise HTTPException(
                status_code=500,
                detail=f"Failed to call tool on MCP server: {str(e)}",
            )

    @staticmethod
    def _build_server_config(mcp_server: MCPServerModel) -> Dict[str, Dict[str, str]]:
        """Build server config for MCP client from database model."""
        config: Dict[str, Any] = {}
        if mcp_server.config:
            try:
                config = json.loads(mcp_server.config)
            except Exception:
                config = {}

        server_config: Dict[str, str] = {
            "url": mcp_server.mcp_url,
            "transport": mcp_server.transport,
        }
        # Merge additional config (e.g., headers, auth)
        server_config.update(config)

        return {mcp_server.name: server_config}

    @staticmethod
    def _to_mcp_server_response(mcp_server: MCPServerModel) -> MCPServerResponse:
        """Convert MCPServerModel to MCPServerResponse."""
        config_dict: Optional[Dict[str, Any]] = None
        if mcp_server.config:
            try:
                config_dict = json.loads(mcp_server.config)
            except Exception:
                config_dict = None

        return MCPServerResponse(
            id=mcp_server.id,
            name=mcp_server.name,
            url=mcp_server.mcp_url,
            transport=mcp_server.transport,
            config=config_dict,
            created_at=str(
                mcp_server.created_at) if mcp_server.created_at else None,
        )
