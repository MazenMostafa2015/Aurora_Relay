"""High-level multi-server MCP client and router facade."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .config import MCPConfig
from .discovery import ToolDiscovery
from .pool import ConnectionPool
from .protocol import ToolDescriptor, ToolNotAllowedError
from .retry import RetryConfig, retry_with_backoff
from .router import ToolRouter

logger = logging.getLogger(__name__)


class MCPClient:
    """Connect, discover, route, retry, health-check, and close MCP servers."""

    def __init__(self, config_path: str | Path | None = None, *, max_connections: int = 10, health_check_interval: float = 60.0) -> None:
        self.config = MCPConfig(config_path)
        self.pool = ConnectionPool(max_connections=max_connections, health_check_interval=health_check_interval)
        self.discovery = ToolDiscovery()
        self.router = ToolRouter()
        self.tool_registry: dict[str, dict[str, Any]] = {}
        self._is_initialized = False

    @property
    def connections(self):
        return self.pool.connections

    async def initialize(self) -> dict[str, bool]:
        statuses: dict[str, bool] = {}
        for server in self.config.servers.values():
            try:
                connection = await self.pool.add(server)
                descriptors = await self.discovery.discover_tools(connection)
                self.tool_registry.update({f"{item.server_name}:{item.name}": item.to_dict() for item in descriptors})
                statuses[server.name] = True
            except Exception as exc:
                statuses[server.name] = False
                logger.error("Failed to initialize %s: %s", server.name, exc)
        self.router.register([self._descriptor_from_dict(item) for item in self.tool_registry.values()])
        self._is_initialized = True
        return statuses

    @staticmethod
    def _descriptor_from_dict(item: dict[str, Any]) -> ToolDescriptor:
        return ToolDescriptor(item["server_name"], item["name"], item.get("description", ""), item.get("input_schema", {}), item.get("annotations", {}))

    async def discover_tools(self) -> list[dict[str, Any]]:
        descriptors = []
        for connection in self.connections.values():
            if connection.state.value == "connected":
                descriptors.extend(await self.discovery.discover_tools(connection))
        self.router.register(descriptors)
        self.tool_registry = self.router.list_all_tools()
        return list(self.tool_registry.values())

    async def call_tool(self, tool_name: str, arguments: dict[str, Any], *, server_name: str | None = None) -> Any:
        descriptor = self.router.resolve(tool_name, server_name)
        server = self.config.get(descriptor.server_name)
        connection = self.pool.get(descriptor.server_name)
        if server is None or connection is None:
            raise RuntimeError(f"Server '{descriptor.server_name}' is not connected")
        if server.allowed_tools and descriptor.name not in server.allowed_tools:
            raise ToolNotAllowedError(f"Tool '{descriptor.name}' is not allowed on server '{descriptor.server_name}'")
        policy = RetryConfig(server.max_retries, server.retry_base_delay)
        return await retry_with_backoff(lambda: connection.call_tool(descriptor.name, arguments), policy)

    async def health_check(self) -> dict[str, bool]:
        return await self.pool.health_check()

    async def close_all(self) -> None:
        await self.pool.close_all()
        self.router.clear()
        self.tool_registry.clear()
        self._is_initialized = False

    async def __aenter__(self) -> "MCPClient":
        await self.initialize()
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        await self.close_all()
