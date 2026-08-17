"""Connection pooling and health monitoring for MCP servers."""
from __future__ import annotations

import asyncio
import logging

from .config import ServerConfig
from .connection import ConnectionState, MCPConnection

logger = logging.getLogger(__name__)


class ConnectionPool:
    def __init__(self, max_connections: int = 10, health_check_interval: float = 60.0) -> None:
        if max_connections < 1:
            raise ValueError("max_connections must be positive")
        self.max_connections = max_connections
        self.health_check_interval = health_check_interval
        self.connections: dict[str, MCPConnection] = {}
        self._health_task: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()

    async def add(self, config: ServerConfig, connect: bool = True) -> MCPConnection:
        async with self._lock:
            if config.name not in self.connections and len(self.connections) >= self.max_connections:
                raise RuntimeError("MCP connection pool is full")
            connection = self.connections.get(config.name) or MCPConnection(config)
            self.connections[config.name] = connection
        if connect:
            await connection.connect()
        return connection

    def get(self, server_name: str) -> MCPConnection | None:
        connection = self.connections.get(server_name)
        return connection if connection and connection.state == ConnectionState.CONNECTED else None

    async def health_check(self) -> dict[str, bool]:
        status: dict[str, bool] = {}
        for name, connection in list(self.connections.items()):
            healthy = await connection.health_check()
            status[name] = healthy
            if not healthy:
                try:
                    await connection.disconnect()
                    await connection.connect()
                    status[name] = True
                except Exception as exc:
                    logger.warning("Reconnect failed for %s: %s", name, exc)
        return status

    def start_health_monitoring(self) -> None:
        if self._health_task is None or self._health_task.done():
            self._health_task = asyncio.create_task(self._monitor())

    async def _monitor(self) -> None:
        try:
            while True:
                await asyncio.sleep(self.health_check_interval)
                await self.health_check()
        except asyncio.CancelledError:
            return

    async def close_all(self) -> None:
        if self._health_task:
            self._health_task.cancel()
            await asyncio.gather(self._health_task, return_exceptions=True)
            self._health_task = None
        for connection in reversed(list(self.connections.values())):
            await connection.disconnect()
        self.connections.clear()
