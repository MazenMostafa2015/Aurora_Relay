"""Shared protocol constants and serialization helpers for the MCP foundation."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class ToolDescriptor:
    """Normalized tool metadata used by discovery and orchestration."""

    server_name: str
    name: str
    description: str = ""
    input_schema: dict[str, Any] = field(default_factory=dict)
    annotations: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def content_text(value: Any) -> str:
    """Extract human-readable text from an MCP result or ordinary value."""
    if isinstance(value, str):
        return value
    content = value.get("content") if isinstance(value, dict) else getattr(value, "content", None)
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                parts.append(str(item.get("text", item)))
            else:
                text = getattr(item, "text", None)
                parts.append(str(text if text is not None else item))
        return "\n".join(parts)
    structured = value.get("structuredContent") if isinstance(value, dict) else getattr(value, "structuredContent", None)
    if isinstance(structured, dict) and "result" in structured:
        return str(structured["result"])
    return str(value)


def error_result(message: str, code: str = "MCP_ERROR") -> dict[str, Any]:
    """Return a consistent structured tool error payload."""
    return {"content": [{"type": "text", "text": message}], "isError": True, "code": code}
