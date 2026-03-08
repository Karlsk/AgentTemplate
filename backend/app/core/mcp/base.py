"""Abstract base class for MCP clients."""

import hashlib
import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List

import structlog
from langchain_mcp_adapters.client import MultiServerMCPClient
from app.core.common.logging import TerraLogUtil


def compute_config_key(server_configs: Dict[str, Dict[str, str]]) -> str:
    """Compute a hash key from server configurations.

    Args:
        server_configs: Server configuration dictionary.

    Returns:
        A hash string representing the configuration.
    """
    config_str = json.dumps(server_configs, sort_keys=True)
    return hashlib.md5(config_str.encode()).hexdigest()


class BaseMCPClient(ABC):
    """Abstract base class for MCP clients.

    Note: As of langchain-mcp-adapters 0.1.0, client caching is not supported.
    Each operation creates a new client instance.
    """

    @abstractmethod
    async def get_client(
        self, server_configs: Dict[str, Dict[str, str]]
    ) -> MultiServerMCPClient:
        """Create an MCP client.

        Args:
            server_configs: Server configuration dictionary.

        Returns:
            A MultiServerMCPClient instance.
        """

    @abstractmethod
    async def get_tools(
        self, server_configs: Dict[str, Dict[str, str]]
    ) -> List[Any]:
        """Get the list of available tools.

        Args:
            server_configs: Server configuration dictionary.

        Returns:
            List of tool objects.
        """

    @abstractmethod
    async def call_tool(
        self,
        server_configs: Dict[str, Dict[str, str]],
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Any:
        """Call a specific tool.

        Args:
            server_configs: Server configuration dictionary.
            tool_name: Name of the tool to call.
            arguments: Tool arguments.

        Returns:
            Tool execution result.
        """

    @abstractmethod
    async def list_skills(
        self, server_configs: Dict[str, Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        """List available skills from the MCP server.

        Args:
            server_configs: Server configuration dictionary.

        Returns:
            List of skill descriptors.
        """

    @abstractmethod
    async def get_skill_schema(
        self, server_configs: Dict[str, Dict[str, str]], skill_name: str
    ) -> Dict[str, Any]:
        """Get the schema for a specific skill.

        Args:
            server_configs: Server configuration dictionary.
            skill_name: Name of the skill to query.

        Returns:
            Skill schema dictionary.
        """

    async def close(self) -> None:
        """Close MCP client connections.

        Note: As of langchain-mcp-adapters 0.1.0, this is a no-op since
        clients are no longer cached and managed.
        """
        pass
