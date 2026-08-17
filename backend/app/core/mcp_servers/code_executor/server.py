"""MCP tools for safe Docker-backed code execution."""
from __future__ import annotations

import json
from typing import Any

from fastmcp import FastMCP

from ...sandbox.config import SandboxConfig
from ...sandbox.manager import SandboxManager

mcp = FastMCP("Code-Executor-Server")
_sandbox_manager: SandboxManager | None = None


async def get_sandbox_manager() -> SandboxManager:
    global _sandbox_manager
    if _sandbox_manager is None:
        _sandbox_manager = SandboxManager(SandboxConfig())
        await _sandbox_manager.initialize()
    return _sandbox_manager


async def _execute(code: str, language: str, timeout: int | None = None, workspace_files: dict[str, str] | None = None) -> dict[str, Any]:
    manager = await get_sandbox_manager()
    container_id = await manager.create_sandbox(language=language, workspace_files=workspace_files)
    try:
        return await manager.execute_code(container_id, code, language, timeout)
    finally:
        await manager.destroy_sandbox(container_id)


@mcp.tool
def sandbox_capabilities() -> dict[str, Any]:
    """Describe enabled languages and sandbox security defaults."""
    return {"languages": ["python", "javascript", "shell"], "network": "none", "read_only_rootfs": True, "requires_docker": True}


@mcp.tool
async def execute_python(code: str, timeout: int = 30) -> dict[str, Any]:
    """Execute Python code in an isolated, resource-limited Docker container."""
    return await _execute(code, "python", timeout)


@mcp.tool
async def execute_javascript(code: str, timeout: int = 30) -> dict[str, Any]:
    """Execute JavaScript with Node.js in an isolated Docker container."""
    return await _execute(code, "javascript", timeout)


@mcp.tool
async def execute_shell(command: str, timeout: int = 30) -> dict[str, Any]:
    """Execute a shell command in an isolated Docker container."""
    return await _execute(command, "shell", timeout)


@mcp.tool
async def execute_with_data(code: str, language: str = "python", data: str | None = None, timeout: int = 30) -> dict[str, Any]:
    """Execute code with JSON or text input exposed as input_data."""
    if language == "python":
        prefix = f"import json\ninput_data = json.loads({json.dumps(data or '')!r}) if isinstance({json.dumps(data or '')!r}, str) else {json.dumps(data or '')!r}\n"
    elif language == "javascript":
        prefix = f"const inputData = {json.dumps(data or '')};\n"
    else:
        prefix = f"export INPUT_DATA={json.dumps(data or '')}\n"
    return await _execute(prefix + code, language, timeout)


@mcp.tool
async def create_file_in_sandbox(filename: str, content: str, language: str = "python", timeout: int = 30) -> dict[str, Any]:
    """Create a workspace file and run a no-op command, returning the captured file list."""
    if filename.startswith("/") or ".." in filename.split("/"):
        raise ValueError("filename must be relative to the sandbox workspace")
    command = "python -c \"from pathlib import Path; print(Path('/workspace').glob('**/*'))\"" if language == "python" else "echo file-created"
    return await _execute(command, language, timeout, {filename: content})


if __name__ == "__main__":
    mcp.run()
