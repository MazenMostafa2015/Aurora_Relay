"""Tool routing across multiple MCP server connections."""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from .protocol import AmbiguousToolError, ToolDescriptor, ToolNotFoundError


class ToolRouter:
    """Maps qualified or unique tool names to their owning server."""

    def __init__(self) -> None:
        self._by_name: dict[str, list[ToolDescriptor]] = defaultdict(list)
        self._by_qualified: dict[str, ToolDescriptor] = {}

    def register(self, descriptors: list[ToolDescriptor]) -> None:
        self.clear()
        for descriptor in descriptors:
            self._by_name[descriptor.name].append(descriptor)
            self._by_qualified[f"{descriptor.server_name}:{descriptor.name}"] = descriptor

    def clear(self) -> None:
        self._by_name.clear()
        self._by_qualified.clear()

    def resolve(self, tool_name: str, server_name: str | None = None) -> ToolDescriptor:
        if server_name:
            descriptor = self._by_qualified.get(f"{server_name}:{tool_name}")
            if descriptor is None:
                raise ToolNotFoundError(f"Tool '{tool_name}' was not found on server '{server_name}'")
            return descriptor
        if ":" in tool_name and tool_name in self._by_qualified:
            return self._by_qualified[tool_name]
        matches = self._by_name.get(tool_name, [])
        if not matches:
            raise ToolNotFoundError(f"Tool '{tool_name}' was not found")
        if len(matches) > 1:
            servers = ", ".join(sorted(item.server_name for item in matches))
            raise AmbiguousToolError(f"Tool '{tool_name}' is exposed by multiple servers: {servers}; use 'server:{tool_name}'")
        return matches[0]

    def list_all_tools(self) -> dict[str, dict[str, Any]]:
        return {key: descriptor.to_dict() for key, descriptor in self._by_qualified.items()}

    def list_server_tools(self, server_name: str) -> list[dict[str, Any]]:
        return [descriptor.to_dict() for descriptor in self._by_qualified.values() if descriptor.server_name == server_name]
