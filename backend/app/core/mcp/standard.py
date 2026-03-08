"""Standard MCP client implementation using MultiServerMCPClient."""

from typing import Any, Dict, List

import structlog
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.tools import BaseTool

from app.core.mcp.base import BaseMCPClient
from app.core.mcp.utils import invoke_tool_with_timeout

from app.core.common.logging import TerraLogUtil


class StandardMCPClient(BaseMCPClient):
    """Standard MCP client using MultiServerMCPClient directly.

    Note: As of langchain-mcp-adapters 0.1.0, MultiServerMCPClient cannot be 
    used as a context manager. Each operation creates a new client instance.
    """

    async def get_client(
        self, server_configs: Dict[str, Dict[str, str]]
    ) -> MultiServerMCPClient:
        """Create a standard MCP client.

        Args:
            server_configs: Server configuration dictionary, e.g.:
                {
                    "server_name": {
                        "url": "http://localhost:8080/sse",
                        "transport": "sse"
                    }
                }

        Returns:
            A MultiServerMCPClient instance.

        Note:
            As of langchain-mcp-adapters 0.1.0, client caching is not supported
            because __aenter__ is no longer available. A new client is created
            for each operation.
        """
        TerraLogUtil.info("mcp_client_creating",
                          server_count=len(server_configs))
        client = MultiServerMCPClient(server_configs)
        TerraLogUtil.info("mcp_client_created")
        return client

    async def get_tools(
        self, server_configs: Dict[str, Dict[str, str]]
    ) -> List[BaseTool]:
        """Get the tool list from standard MCP servers.

        Args:
            server_configs: Server configuration dictionary.

        Returns:
            List of tool objects.
        """
        client = MultiServerMCPClient(server_configs)
        tools = await client.get_tools()
        TerraLogUtil.info("mcp_tools_retrieved", tool_count=len(tools))
        return tools

    async def call_tool(
        self,
        server_configs: Dict[str, Dict[str, str]],
        tool_name: str,
        arguments: Dict[str, Any],
        timeout: int = 10,
        retries: int = 2,
    ) -> Any:
        """Call a tool on a standard MCP server with timeout and retry.

        Args:
            server_configs: Server configuration dictionary.
            tool_name: Name of the tool to call.
            arguments: Tool arguments.
            timeout: Timeout per invocation attempt in seconds, default 10.
            retries: Number of retry attempts, default 2.

        Returns:
            Tool execution result.

        Raises:
            ValueError: If the tool is not found.
            RuntimeError: If the tool execution fails after retries.
        """
        tools = await self.get_tools(server_configs)
        target_tool = None
        for tool in tools:
            if hasattr(tool, "name") and tool.name == tool_name:
                target_tool = tool
                break

        if target_tool is None:
            TerraLogUtil.error("mcp_tool_not_found", tool_name=tool_name)
            raise ValueError(
                f"Tool '{tool_name}' not found in available tools")

        TerraLogUtil.info("mcp_tool_calling", tool_name=tool_name,
                          timeout=timeout, retries=retries)
        result = await invoke_tool_with_timeout(
            target_tool, arguments, timeout=timeout, retries=retries
        )

        if not result["ok"]:
            TerraLogUtil.error("mcp_tool_call_failed",
                               tool_name=tool_name, error=result["error"])
            raise RuntimeError(result["error"])

        TerraLogUtil.info("mcp_tool_call_success",
                          tool_name=tool_name, elapsed_ms=result["elapsed_ms"])
        return result["payload"]

    async def list_skills(
        self, server_configs: Dict[str, Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        """Not supported by standard MCP client.

        Raises:
            NotImplementedError: Standard MCP does not support list_skills.
        """
        raise NotImplementedError(
            "list_skills is not supported by standard MCP client")

    async def get_skill_schema(
        self, server_configs: Dict[str, Dict[str, str]], skill_name: str
    ) -> Dict[str, Any]:
        """Not supported by standard MCP client.

        Raises:
            NotImplementedError: Standard MCP does not support get_skill_schema.
        """
        raise NotImplementedError(
            "get_skill_schema is not supported by standard MCP client")
