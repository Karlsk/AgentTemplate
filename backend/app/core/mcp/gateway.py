"""MCP Gateway client implementation.

This client communicates via HTTP gateway endpoints, using the gateway's
list_skills() and get_skill_schema() APIs to discover and invoke tools.
"""

from typing import Any, Dict, List

import structlog
from langchain_mcp_adapters.client import MultiServerMCPClient

from app.core.mcp.base import BaseMCPClient, compute_config_key
from app.core.common.logging import TerraLogUtil


class GatewayMCPClient(BaseMCPClient):
    """MCP Gateway client that communicates via HTTP gateway endpoints.

    This client uses the gateway's list_skills() and get_skill_schema() APIs
    to discover and invoke tools.
    """

    async def get_client(
        self, server_configs: Dict[str, Dict[str, str]]
    ) -> MultiServerMCPClient:
        """Get or create an MCP Gateway client.

        Args:
            server_configs: Server configuration dictionary.

        Returns:
            A MultiServerMCPClient instance.

        TODO: Implement gateway-specific client initialization.
        """
        config_key = compute_config_key(server_configs)

        if config_key in self._clients:
            return self._clients[config_key]

        TerraLogUtil.info("mcp_gateway_client_creating",
                          server_count=len(server_configs))

        # TODO: Implement gateway-specific client creation.
        # Gateway clients may need to call list_skills() and get_skill_schema()
        # via HTTP to discover available tools before creating the client.
        client = MultiServerMCPClient(server_configs)
        await client.__aenter__()
        self._clients[config_key] = client

        TerraLogUtil.info("mcp_gateway_client_created", config_key=config_key)
        return client

    async def get_tools(
        self, server_configs: Dict[str, Dict[str, str]]
    ) -> List[Any]:
        """Get the tool list from the MCP Gateway.

        Args:
            server_configs: Server configuration dictionary.

        Returns:
            List of tool objects.

        TODO: Implement gateway tool discovery via list_skills() and get_skill_schema().
        """
        # TODO: Implement via HTTP calls to gateway's list_skills() and get_skill_schema()
        TerraLogUtil.warning("mcp_gateway_get_tools_not_implemented")
        return []

    async def call_tool(
        self,
        server_configs: Dict[str, Dict[str, str]],
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Any:
        """Call a tool via the MCP Gateway.

        Args:
            server_configs: Server configuration dictionary.
            tool_name: Name of the tool to call.
            arguments: Tool arguments.

        Returns:
            Tool execution result.

        Raises:
            NotImplementedError: Gateway call_tool is not yet implemented.

        TODO: Implement gateway tool invocation.
        """
        # TODO: Implement via HTTP call to gateway's tool execution endpoint
        TerraLogUtil.warning(
            "mcp_gateway_call_tool_not_implemented",
            tool_name=tool_name,
        )
        raise NotImplementedError(
            "MCP Gateway call_tool is not yet implemented"
        )

    async def list_skills(
        self, server_configs: Dict[str, Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        """List available skills from the MCP Gateway.

        Args:
            server_configs: Server configuration dictionary.

        Returns:
            List of skill descriptors.

        TODO: Implement via HTTP call to gateway's list_skills endpoint.
        """
        # TODO: Implement via HTTP call to gateway's list_skills endpoint
        TerraLogUtil.warning("mcp_gateway_list_skills_not_implemented")
        return []

    async def get_skill_schema(
        self, server_configs: Dict[str, Dict[str, str]], skill_name: str
    ) -> Dict[str, Any]:
        """Get the schema for a specific skill from the MCP Gateway.

        Args:
            server_configs: Server configuration dictionary.
            skill_name: Name of the skill to query.

        Returns:
            Skill schema dictionary.

        TODO: Implement via HTTP call to gateway's get_skill_schema endpoint.
        """
        # TODO: Implement via HTTP call to gateway's get_skill_schema endpoint
        TerraLogUtil.warning(
            "mcp_gateway_get_skill_schema_not_implemented",
            skill_name=skill_name,
        )
        return {}
