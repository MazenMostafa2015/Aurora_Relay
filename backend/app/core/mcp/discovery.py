"""Tool discovery and normalization for connected MCP servers."""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .connection import MCPConnection
from .protocol import ToolDescriptor


class ToolDiscovery:
    """Queries ``tools/list`` and converts SDK models to stable dictionaries."""

    async def discover_tools(self, connection: MCPConnection) -> list[ToolDescriptor]:
        result = await connection.list_tools()
        allowed = set(connection.config.allowed_tools)
        descriptors: list[ToolDescriptor] = []
        for tool in getattr(result, "tools", []):
            name = str(tool.name)
            if allowed and name not in allowed:
                continue
            annotations = getattr(tool, "annotations", {}) or {}
            if hasattr(annotations, "model_dump"):
                annotations = annotations.model_dump()
            elif not isinstance(annotations, dict):
                annotations = {key: value for key, value in vars(annotations).items() if not key.startswith("_")}
            schema = getattr(tool, "inputSchema", getattr(tool, "input_schema", {})) or {}
            descriptors.append(ToolDescriptor(connection.name, name, tool.description or "", schema, annotations))
        return descriptors

    @staticmethod
    def index(descriptors: list[ToolDescriptor]) -> dict[str, dict[str, Any]]:
        return {f"{item.server_name}:{item.name}": asdict(item) for item in descriptors}
