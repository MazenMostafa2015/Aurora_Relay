"""One MCP server connection backed by the official Python SDK."""
from __future__ import annotations

import asyncio
import logging
import os
from contextlib import AsyncExitStack
from enum import Enum
from typing import Any

from .config import ServerConfig
from .protocol import ConnectionError, ConnectionTimeoutError, ToolExecutionError

logger = logging.getLogger(__name__)


class ConnectionState(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    CLOSING = "closing"


class MCPConnection:
    """Owns one SDK session and its stdio subprocess transport."""

    def __init__(self, config: ServerConfig) -> None:
        self.config = config
        self.name = config.name
        self.state = ConnectionState.DISCONNECTED
        self.session: Any | None = None
        self._stack: AsyncExitStack | None = None
        self.server_info: Any | None = None
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        async with self._lock:
            if self.state == ConnectionState.CONNECTED:
                return
            self.state = ConnectionState.CONNECTING
            try:
                from mcp import ClientSession, StdioServerParameters
                from mcp.client.stdio import stdio_client

                env = {**os.environ, **self.config.env}
                params = StdioServerParameters(command=self.config.command, args=self.config.args, env=env)
                stack = AsyncExitStack()
                await stack.__aenter__()
                transport = await stack.enter_async_context(stdio_client(params))
                session = await stack.enter_async_context(ClientSession(*transport))
                async with asyncio.timeout(self.config.timeout):
                    initialize_result = await session.initialize()
                self._stack = stack
                self.session = session
                self.server_info = getattr(initialize_result, "server_info", None)
                self.state = ConnectionState.CONNECTED
                logger.info("Connected to MCP server %s", self.name)
            except asyncio.TimeoutError as exc:
                self.state = ConnectionState.ERROR
                await self._close_stack()
                raise ConnectionTimeoutError(f"Initialization timed out for server '{self.name}'") from exc
            except Exception as exc:
                self.state = ConnectionState.ERROR
                await self._close_stack()
                raise ConnectionError(f"Failed to connect to server '{self.name}': {exc}") from exc

    async def list_tools(self) -> Any:
        session = self._require_session()
        try:
            async with asyncio.timeout(self.config.timeout):
                return await session.list_tools()
        except asyncio.TimeoutError as exc:
            raise ConnectionTimeoutError(f"tools/list timed out for server '{self.name}'") from exc

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        session = self._require_session()
        try:
            async with asyncio.timeout(self.config.timeout):
                result = await session.call_tool(tool_name, arguments)
        except asyncio.TimeoutError as exc:
            raise ConnectionTimeoutError(f"Tool '{tool_name}' timed out on server '{self.name}'") from exc
        if getattr(result, "is_error", False):
            text = "\n".join(getattr(item, "text", str(item)) for item in getattr(result, "content", []))
            raise ToolExecutionError(f"Tool '{tool_name}' failed on '{self.name}': {text}")
        return result

    async def health_check(self) -> bool:
        if self.state != ConnectionState.CONNECTED:
            return False
        try:
            await self.list_tools()
            return True
        except Exception:
            self.state = ConnectionState.ERROR
            return False

    async def disconnect(self) -> None:
        async with self._lock:
            if self.state == ConnectionState.DISCONNECTED and self._stack is None:
                return
            self.state = ConnectionState.CLOSING
            await self._close_stack()
            self.session = None
            self.state = ConnectionState.DISCONNECTED
            logger.info("Disconnected from MCP server %s", self.name)

    async def _close_stack(self) -> None:
        if self._stack is not None:
            try:
                await self._stack.aclose()
            finally:
                self._stack = None

    def _require_session(self) -> Any:
        if self.state != ConnectionState.CONNECTED or self.session is None:
            raise ConnectionError(f"Server '{self.name}' is not connected")
        return self.session

    async def __aenter__(self) -> "MCPConnection":
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        await self.disconnect()
