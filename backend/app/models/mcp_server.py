"""MCP Server database model."""

from enum import Enum

from sqlalchemy import Column, String, Text
from sqlmodel import Field

from app.models.base import BaseModel


class McpTransportType(str, Enum):
    """MCP transport type enumeration."""

    STREAMABLE_HTTP = "streamable_http"
    SSE = "sse"
    STDIO = "stdio"
    GATEWAY = "gateway"


class MCPServerModel(BaseModel, table=True):
    """MCP Server model for storing MCP server configuration.

    Attributes:
        id: The primary key.
        name: MCP server name.
        mcp_url: MCP server URL.
        transport: MCP server transport type (sse/streamable_http/stdio/gateway).
        config: JSON format for additional parameters and authentication info.
        created_at: When the MCP server was created.
    """

    __tablename__ = "mcp_server"

    id: int = Field(default=None, primary_key=True)
    name: str = Field(sa_column=Column(String(255), nullable=False))
    mcp_url: str = Field(sa_column=Column(String(255), nullable=False))
    transport: str = Field(
        default=McpTransportType.STREAMABLE_HTTP.value,
        sa_column=Column(String(255), nullable=False),
    )
    config: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True))
