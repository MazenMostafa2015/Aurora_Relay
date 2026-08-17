"""Workspace-restricted filesystem MCP server."""
from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

from fastmcp import FastMCP

from mcp_servers.common.error_handler import PermissionDeniedError, ValidationError, configure_logging, handle_mcp_error

mcp = FastMCP("Filesystem-Server")
logger = configure_logging(os.getenv("MCP_LOG_PATH"))


def workspace_root() -> Path:
    root = Path(os.getenv("WORKSPACE_DIR", "./workspace")).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def safe_path(path: str) -> Path:
    if not path or "\x00" in path:
        raise ValidationError("path must be a non-empty safe path.")
    root = workspace_root()
    candidate = (root / path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise PermissionDeniedError("Path must remain inside the configured workspace directory.") from exc
    return candidate


def result(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)


@mcp.tool(annotations={"readOnlyHint": True})
@handle_mcp_error
async def read_file(path: str) -> str:
    """Read UTF-8 text from a workspace file."""
    target = safe_path(path)
    if not target.is_file():
        raise ValidationError(f"File does not exist: {path}")
    return target.read_text(encoding="utf-8")


@mcp.tool
@handle_mcp_error
async def write_file(path: str, content: str) -> str:
    """Create or overwrite a UTF-8 text file inside the workspace."""
    target = safe_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return result({"path": str(target.relative_to(workspace_root())), "bytes": target.stat().st_size, "written": True})


@mcp.tool(annotations={"readOnlyHint": True})
@handle_mcp_error
async def list_directory(path: str = ".") -> str:
    """List immediate workspace directory entries with type and size metadata."""
    target = safe_path(path)
    if not target.is_dir():
        raise ValidationError(f"Directory does not exist: {path}")
    entries = []
    for item in sorted(target.iterdir(), key=lambda p: p.name.lower()):
        entries.append({"name": item.name, "type": "directory" if item.is_dir() else "file", "size": item.stat().st_size if item.is_file() else None})
    return result({"path": str(target.relative_to(workspace_root())), "entries": entries})


@mcp.tool(annotations={"destructiveHint": True})
@handle_mcp_error
async def delete_file(path: str) -> str:
    """Delete a file or an empty directory inside the workspace."""
    target = safe_path(path)
    if not target.exists():
        raise ValidationError(f"Path does not exist: {path}")
    if target.is_dir():
        target.rmdir()
    else:
        target.unlink()
    return result({"path": str(target.relative_to(workspace_root())), "deleted": True})


@mcp.tool(annotations={"readOnlyHint": True})
@handle_mcp_error
async def get_file_info(path: str) -> str:
    """Return file or directory metadata, including size, mode, and modification time."""
    target = safe_path(path)
    if not target.exists():
        raise ValidationError(f"Path does not exist: {path}")
    stat = target.stat()
    return result({"path": str(target.relative_to(workspace_root())), "type": "directory" if target.is_dir() else "file", "size": stat.st_size, "mode": oct(stat.st_mode & 0o777), "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()})


if __name__ == "__main__":
    mcp.run(transport=os.getenv("MCP_TRANSPORT", "stdio"))
