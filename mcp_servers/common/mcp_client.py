"""Async MCP client manager using the official Python SDK and stdio transport."""
from __future__ import annotations

import asyncio
import json
import os
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

from .protocol import ToolDescriptor


class MCPClient:
    """Manages connections to MCP servers and tool discovery."""

    def __init__(self, server_config_path: str | Path) -> None:
        self.server_config_path = Path(server_config_path)
        payload = json.loads(self.server_config_path.read_text(encoding="utf-8"))
        self.config: dict[str, Any] = payload.get("mcpServers", payload)
        self.sessions: dict[str, Any] = {}
        self._stack: AsyncExitStack | None = None
        self._transports: dict[str, Any] = {}
        self._tools: dict[str, list[ToolDescriptor]] = {}

    async def connect_all_servers(self) -> dict[str, bool]:
        """Establish connections to all configured stdio servers."""
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
        except ImportError as exc:
            raise RuntimeError("Install the official 'mcp' package to use MCPClient") from exc
        self._stack = AsyncExitStack()
        await self._stack.__aenter__()
        statuses: dict[str, bool] = {}
        for name, cfg in self.config.items():
            try:
                env = {**os.environ, **cfg.get("env", {})}
                params = StdioServerParameters(command=cfg["command"], args=cfg.get("args", []), env=env)
                transport = await self._stack.enter_async_context(stdio_client(params))
                session = await self._stack.enter_async_context(ClientSession(*transport))
                await session.initialize()
                self.sessions[name] = session
                statuses[name] = True
            except Exception:
                statuses[name] = False
        return statuses

    async def discover_tools(self) -> list[dict[str, Any]]:
        discovered: list[dict[str, Any]] = []
        for server_name, session in self.sessions.items():
            result = await session.list_tools()
            allowed = set(self.config[server_name].get("allowedTools", []))
            descriptors = []
            for tool in result.tools:
                if allowed and tool.name not in allowed:
                    continue
                raw_annotations = getattr(tool, "annotations", {}) or {}
                if hasattr(raw_annotations, "model_dump"):
                    raw_annotations = raw_annotations.model_dump()
                elif not isinstance(raw_annotations, dict):
                    raw_annotations = {key: value for key, value in vars(raw_annotations).items() if not key.startswith("_")}
                descriptor = ToolDescriptor(server_name=server_name, name=tool.name, description=tool.description or "", input_schema=getattr(tool, "inputSchema", {}) or {}, annotations=raw_annotations)
                descriptors.append(descriptor)
                discovered.append(descriptor.to_dict())
            self._tools[server_name] = descriptors
        return discovered

    async def call_tool(self, server_name: str, tool_name: str, arguments: dict[str, Any]) -> Any:
        if server_name not in self.sessions:
            raise KeyError(f"Server is not connected: {server_name}")
        allowed = set(self.config[server_name].get("allowedTools", []))
        if allowed and tool_name not in allowed:
            raise PermissionError(f"Tool '{tool_name}' is not allowed on server '{server_name}'")
        return await self.sessions[server_name].call_tool(tool_name, arguments)

    async def get_server_health(self) -> dict[str, bool]:
        health: dict[str, bool] = {}
        for name, session in self.sessions.items():
            try:
                await session.list_tools()
                health[name] = True
            except Exception:
                health[name] = False
        return health

    async def close(self) -> None:
        if self._stack:
            await self._stack.aclose()
            self._stack = None
            self.sessions.clear()

    async def __aenter__(self) -> "MCPClient":
        await self.connect_all_servers()
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        await self.close()


async def client_healthcheck(config_path: str | Path) -> dict[str, bool]:
    async with MCPClient(config_path) as client:
        return await client.get_server_health()
