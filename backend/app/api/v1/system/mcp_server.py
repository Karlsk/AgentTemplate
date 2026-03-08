"""MCP Server API endpoints."""

from typing import List

from fastapi import APIRouter, Path, Request

from app.core.common.config import settings
from app.core.common.deps import CurrentUser, SessionDep
from app.core.common.limiter import limiter
from app.core.common.permissions import require_permissions
from app.schemas.mcp_server import (
    MCPServerCreate,
    MCPServerUpdate,
    MCPServerResponse,
    MCPServerGridItem,
    ToolCallRequest,
    ToolCallResponse,
    ToolInfo,
)
from app.services.system import SystemService

router = APIRouter(tags=["system_mcp_server"], prefix="/system/mcp-server")
system_service = SystemService()


@router.post(
    "/servers",
    response_model=MCPServerResponse,
    summary="create_mcp_server",
    description="Create a new MCP server configuration",
)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["mcp_server"][0])
@require_permissions(roles=["admin"])
async def create_mcp_server(
    request: Request,
    mcp_server: MCPServerCreate,
    current_user: CurrentUser,
    session: SessionDep,
):
    """Create a new MCP server configuration."""
    return await system_service.create_mcp_server(
        session=session, info=mcp_server, current_user=current_user
    )


@router.get(
    "/servers/{server_id}",
    response_model=MCPServerResponse,
    summary="get_mcp_server_by_id",
    description="Get MCP server by ID",
)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["mcp_server"][0])
@require_permissions(roles=["admin"])
async def get_mcp_server_by_id(
    request: Request,
    server_id: int = Path(..., title="The ID of the MCP server to retrieve"),
    current_user: CurrentUser = None,
    session: SessionDep = None,
):
    """Get MCP server by ID."""
    return await system_service.get_mcp_server_by_id(
        session=session, server_id=server_id
    )


@router.get(
    "/servers",
    response_model=List[MCPServerGridItem],
    summary="get_mcp_servers",
    description="Get all MCP servers",
)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["mcp_server"][0])
@require_permissions(roles=["admin"])
async def get_mcp_servers(
    request: Request,
    current_user: CurrentUser,
    session: SessionDep,
):
    """Get all MCP servers."""
    return await system_service.get_mcp_servers(session=session)


@router.put(
    "/servers",
    response_model=MCPServerResponse,
    summary="update_mcp_server",
    description="Update an existing MCP server configuration",
)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["mcp_server"][0])
@require_permissions(roles=["admin"])
async def update_mcp_server(
    request: Request,
    mcp_server: MCPServerUpdate,
    current_user: CurrentUser,
    session: SessionDep,
):
    """Update an existing MCP server configuration."""
    return await system_service.update_mcp_server(
        session=session, info=mcp_server, current_user=current_user
    )


@router.delete(
    "/servers/{server_id}",
    response_model=MCPServerResponse,
    summary="delete_mcp_server",
    description="Delete an MCP server configuration",
)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["mcp_server"][0])
@require_permissions(roles=["admin"])
async def delete_mcp_server(
    request: Request,
    server_id: int = Path(..., title="The ID of the MCP server to delete"),
    current_user: CurrentUser = None,
    session: SessionDep = None,
):
    """Delete an MCP server configuration."""
    return await system_service.delete_mcp_server(
        session=session, server_id=server_id, current_user=current_user
    )


@router.get(
    "/servers/{server_id}/tools",
    response_model=List[ToolInfo],
    summary="get_mcp_server_tools",
    description="Get available tools from an MCP server",
)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["mcp_server"][0])
@require_permissions(roles=["admin"])
async def get_available_tools(
    request: Request,
    server_id: int = Path(..., title="The ID of the MCP server"),
    current_user: CurrentUser = None,
    session: SessionDep = None,
):
    """Get available tools from an MCP server."""
    return await system_service.get_mcp_server_tools(
        session=session, server_id=server_id
    )


@router.post(
    "/servers/{server_id}/tools/call",
    response_model=ToolCallResponse,
    summary="call_mcp_server_tool",
    description="Call a tool on an MCP server",
)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["mcp_server"][0])
@require_permissions(roles=["admin"])
async def call_tool(
    request: Request,
    tool_call_request: ToolCallRequest,
    server_id: int = Path(..., title="The ID of the MCP server"),
    current_user: CurrentUser = None,
    session: SessionDep = None,
):
    """Call a tool on the specified MCP server.

    This endpoint invokes a tool on the MCP server with the provided arguments.
    The call includes timeout and retry protection.
    """
    return await system_service.call_mcp_server_tool(
        session=session,
        server_id=server_id,
        tool_name=tool_call_request.tool_name,
        arguments=tool_call_request.arguments,
    )
