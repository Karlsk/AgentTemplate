"""MCP client factory for creating the appropriate client based on configuration."""

from typing import Any, Dict, Type


from app.core.mcp.base import BaseMCPClient
from app.core.mcp.gateway import GatewayMCPClient
from app.core.mcp.standard import StandardMCPClient

from app.core.common.logging import TerraLogUtil


class MCPClientFactory:
    """Factory class for creating and managing MCP client instances.

    Maintains a registry of client types and caches singleton instances
    per type to avoid redundant object creation.

    Example:
        mcp_config = {
            "type": "standard",
            "my_server": {
                "url": "http://localhost:8080/sse",
                "transport": "sse"
            }
        }
        client = MCPClientFactory.create(mcp_config)
        tools = await client.get_tools(server_configs)
    """

    _registry: Dict[str, Type[BaseMCPClient]] = {
        "standard": StandardMCPClient,
        "gateway": GatewayMCPClient,
    }

    _instances: Dict[str, BaseMCPClient] = {}

    @classmethod
    def create(cls, mcp_config: Dict[str, Any]) -> BaseMCPClient:
        """Create or retrieve an MCP client based on configuration.

        Args:
            mcp_config: MCP configuration dictionary. Must contain a "type" key
                ("standard" or "gateway"). Remaining keys are server configs.
                Example::

                    {
                        "type": "standard",
                        "server_name": {
                            "url": "http://localhost:8080/sse",
                            "transport": "sse"
                        }
                    }

        Returns:
            An instance of BaseMCPClient matching the requested type.

        Raises:
            ValueError: If the MCP type is not registered.
        """
        mcp_type = mcp_config.get("type", "standard")

        if mcp_type not in cls._registry:
            raise ValueError(
                f"Unsupported MCP type: '{mcp_type}'. "
                f"Supported types: {list(cls._registry.keys())}"
            )

        if mcp_type not in cls._instances:
            client_class = cls._registry[mcp_type]
            cls._instances[mcp_type] = client_class()
            TerraLogUtil.info("mcp_client_factory_created", mcp_type=mcp_type)

        return cls._instances[mcp_type]

    @classmethod
    def register(cls, mcp_type: str, client_class: Type[BaseMCPClient]) -> None:
        """Register a new MCP client type.

        Args:
            mcp_type: The type identifier string.
            client_class: The client class to associate with the type.
        """
        cls._registry[mcp_type] = client_class
        TerraLogUtil.info("mcp_client_type_registered", mcp_type=mcp_type)

    @classmethod
    async def close_all(cls) -> None:
        """Close all cached client instances and clear the cache."""
        for mcp_type, instance in cls._instances.items():
            try:
                await instance.close()
                TerraLogUtil.info(
                    "mcp_client_instance_closed", mcp_type=mcp_type)
            except Exception:
                TerraLogUtil.exception(
                    "mcp_client_instance_close_failed", mcp_type=mcp_type)
        cls._instances.clear()
