"""MCP Server schemas for request and response models."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.schemas.base import BaseEditDTO


class MCPServerCreate(BaseModel):
    """Create MCP server request model."""

    name: str = Field(..., description="MCP server name", max_length=255)
    url: str = Field(..., description="MCP server URL", max_length=255)
    transport: str = Field(
        default="streamable_http",
        description="Transport type: streamable_http, sse, stdio, gateway",
    )
    config: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional parameters and authentication info"
    )


class MCPServerUpdate(BaseModel):
    """Update MCP server request model."""

    id: int = Field(..., description="MCP server ID")
    name: Optional[str] = Field(
        None, description="MCP server name", max_length=255)
    url: Optional[str] = Field(
        None, description="MCP server URL", max_length=255)
    transport: Optional[str] = Field(
        None, description="Transport type: streamable_http, sse, stdio, gateway"
    )
    config: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional parameters and authentication info"
    )


class MCPServerResponse(BaseModel):
    """MCP server response model."""

    id: int
    name: str
    url: str
    transport: str
    config: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class MCPServerGridItem(BaseModel):
    """MCP server grid item for list display."""

    id: int
    name: str
    url: str
    transport: str
    created_at: Optional[datetime] = None


class ToolCallRequest(BaseModel):
    """Tool call request model."""

    tool_name: str = Field(..., description="Name of the tool to call")
    arguments: Dict[str, Any] = Field(
        default_factory=dict, description="Tool arguments"
    )


class ToolInfo(BaseModel):
    """Tool information model."""

    name: str = Field(..., description="Tool name")
    description: str = Field(default="", description="Tool description")
    args_schema: Optional[Dict[str, Any]] = Field(
        default=None, description="Tool arguments schema"
    )


class ToolCallResponse(BaseModel):
    """Tool call response model."""

    ok: bool = Field(..., description="Whether the call succeeded")
    result: Optional[Any] = Field(
        default=None, description="Tool execution result")
    error: Optional[str] = Field(
        default=None, description="Error message if failed")
    elapsed_ms: Optional[float] = Field(
        default=None, description="Execution time in ms")
