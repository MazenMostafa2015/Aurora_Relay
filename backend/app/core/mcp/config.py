"""Configuration management for multiple MCP stdio servers."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .protocol import ConfigurationError


@dataclass(slots=True)
class ServerConfig:
    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    allowed_tools: list[str] = field(default_factory=list)
    timeout: float = 30.0
    max_retries: int = 2
    retry_base_delay: float = 0.25

    @classmethod
    def from_dict(cls, name: str, value: dict[str, Any]) -> "ServerConfig":
        command = str(value.get("command", "")).strip()
        if not command:
            raise ConfigurationError(f"Server '{name}' must define a command")
        args = value.get("args", [])
        if not isinstance(args, list) or not all(isinstance(item, str) for item in args):
            raise ConfigurationError(f"Server '{name}' args must be a list of strings")
        timeout = float(value.get("timeout", 30.0))
        if timeout <= 0:
            raise ConfigurationError(f"Server '{name}' timeout must be positive")
        retries = int(value.get("maxRetries", value.get("max_retries", 2)))
        if retries < 0:
            raise ConfigurationError(f"Server '{name}' maxRetries cannot be negative")
        raw_env = value.get("env", {})
        if not isinstance(raw_env, dict):
            raise ConfigurationError(f"Server '{name}' env must be an object")
        env = {str(key): os.path.expandvars(str(item)) for key, item in raw_env.items()}
        return cls(
            name=name,
            command=command,
            args=args,
            env=env,
            allowed_tools=[str(item) for item in value.get("allowedTools", value.get("allowed_tools", []))],
            timeout=timeout,
            max_retries=retries,
            retry_base_delay=float(value.get("retryBaseDelay", value.get("retry_base_delay", 0.25))),
        )

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["allowedTools"] = result.pop("allowed_tools")
        result["maxRetries"] = result.pop("max_retries")
        result["retryBaseDelay"] = result.pop("retry_base_delay")
        return result


class MCPConfig:
    """Loads and persists an ``mcpServers`` configuration document."""

    def __init__(self, config_path: str | Path | None = None) -> None:
        self.config_path = Path(config_path) if config_path else Path.cwd() / "backend" / "app" / "config" / "mcp_servers.json"
        self.servers: dict[str, ServerConfig] = {}
        self._load()

    def _load(self) -> None:
        if not self.config_path.exists():
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            self._save()
            return
        try:
            payload = json.loads(self.config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ConfigurationError(f"Could not load MCP config {self.config_path}: {exc}") from exc
        raw_servers = payload.get("mcpServers", payload)
        if not isinstance(raw_servers, dict):
            raise ConfigurationError("MCP configuration must contain an 'mcpServers' object")
        self.servers = {name: ServerConfig.from_dict(name, value) for name, value in raw_servers.items()}

    def _save(self) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"mcpServers": {name: server.to_dict() for name, server in self.servers.items()}}
        self.config_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def get(self, server_name: str) -> ServerConfig | None:
        return self.servers.get(server_name)

    def add_server(self, server_name: str, config: dict[str, Any] | ServerConfig) -> ServerConfig:
        server = config if isinstance(config, ServerConfig) else ServerConfig.from_dict(server_name, config)
        self.servers[server_name] = server
        self._save()
        return server

    def remove_server(self, server_name: str) -> bool:
        removed = self.servers.pop(server_name, None) is not None
        if removed:
            self._save()
        return removed

    def as_dict(self) -> dict[str, Any]:
        return {"mcpServers": {name: server.to_dict() for name, server in self.servers.items()}}
