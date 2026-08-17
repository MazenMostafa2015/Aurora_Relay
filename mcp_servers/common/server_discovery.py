"""MCP server configuration discovery and manifest generation."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class DiscoveredServer(dict[str, Any]):
    @property
    def name(self) -> str:
        return str(self["name"])


class ServerDiscovery:
    """Discovers and registers MCP servers dynamically."""

    def __init__(self, registry_path: str | Path | None = None) -> None:
        self.registry_path = Path(registry_path) if registry_path else None
        self.servers: dict[str, dict[str, Any]] = {}

    def discover(self) -> list[dict[str, Any]]:
        """Synchronously discover servers from the configured JSON registry."""
        if not self.registry_path or not self.registry_path.exists():
            return list(self.servers.values())
        payload = json.loads(self.registry_path.read_text(encoding="utf-8"))
        entries = payload.get("mcpServers", payload if isinstance(payload, dict) else {})
        for name, config in entries.items():
            self.servers[name] = DiscoveredServer(name=name, **config, config_path=str(self.registry_path))
        return list(self.servers.values())

    async def discover_from_directory(self, path: str | Path) -> list[dict[str, Any]]:
        directory = Path(path)
        discovered: list[dict[str, Any]] = []
        for config_path in sorted(directory.glob("*.json")):
            try:
                payload = json.loads(config_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            entries = payload.get("mcpServers", payload if isinstance(payload, dict) else {})
            for name, config in entries.items():
                item = DiscoveredServer(name=name, **config, config_path=str(config_path))
                self.servers[name] = item
                discovered.append(item)
        return discovered

    async def discover_from_registry(self) -> list[dict[str, Any]]:
        if not self.registry_path or not self.registry_path.exists():
            return list(self.servers.values())
        payload = json.loads(self.registry_path.read_text(encoding="utf-8"))
        entries = payload.get("mcpServers", payload if isinstance(payload, dict) else {})
        for name, config in entries.items():
            self.servers[name] = DiscoveredServer(name=name, **config, config_path=str(self.registry_path))
        return list(self.servers.values())

    async def generate_manifest(self) -> dict[str, Any]:
        return {"servers": list(self.servers.values()), "server_count": len(self.servers)}
