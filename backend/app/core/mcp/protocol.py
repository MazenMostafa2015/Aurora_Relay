"""Protocol models and errors used by the Phase 2 MCP client."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class ToolDescriptor:
    server_name: str
    name: str
    description: str = ""
    input_schema: dict[str, Any] = field(default_factory=dict)
    annotations: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class MCPMessage:
    """JSON-RPC 2.0 request, response, or notification envelope."""

    jsonrpc: str = "2.0"
    method: str | None = None
    params: dict[str, Any] | None = None
    id: int | str | None = None
    result: Any | None = None
    error: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {key: value for key, value in asdict(self).items() if value is not None}

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "MCPMessage":
        return cls(**payload)


class MCPClientError(Exception):
    """Base class for client-side MCP failures."""


class ConfigurationError(MCPClientError):
    """Raised when server configuration is missing or invalid."""


class ConnectionError(MCPClientError):
    """Raised when an MCP server cannot be connected or has disconnected."""


class ConnectionTimeoutError(ConnectionError):
    """Raised when a request exceeds its configured timeout."""


class ToolNotFoundError(MCPClientError):
    """Raised when no registered server exposes a requested tool."""


class AmbiguousToolError(MCPClientError):
    """Raised when more than one server exposes the same unqualified tool."""


class ToolNotAllowedError(MCPClientError):
    """Raised when an allowlist blocks a tool call."""


class ToolExecutionError(MCPClientError):
    """Raised when an MCP tool returns an error result."""
