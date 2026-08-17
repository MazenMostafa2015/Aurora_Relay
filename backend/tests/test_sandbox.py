from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.core.mcp_servers.code_executor.server import mcp
from app.core.sandbox.config import NetworkAccess, SandboxConfig
from app.core.sandbox.filesystem import SandboxFilesystem
from app.core.sandbox.manager import SandboxManager
from app.core.sandbox.resources import ResourceLimits


def test_config_defaults_are_hardened():
    config = SandboxConfig()
    kwargs = config.to_docker_kwargs(workspace_host="/tmp/workspace")
    assert kwargs["network_mode"] == "none"
    assert kwargs["read_only"] is True
    assert kwargs["cap_drop"] == ["ALL"]
    assert kwargs["pids_limit"] == 128
    assert kwargs["security_opt"] == ["no-new-privileges:true"]


def test_config_rejects_unsafe_limits():
    with pytest.raises(ValueError):
        SandboxConfig(timeout_seconds=0)
    with pytest.raises(ValueError):
        SandboxConfig(network_access=NetworkAccess.LOCALHOST, network_mode="host")


def test_workspace_rejects_traversal(tmp_path):
    fs = SandboxFilesystem(tmp_path)
    with pytest.raises(PermissionError):
        fs.safe_path("../outside.txt")
    staged = fs.stage_files({"nested/input.txt": "hello"})
    assert (staged / "nested/input.txt").read_text() == "hello"
    fs.cleanup(staged)


def test_resource_limits_truncate_output():
    limits = ResourceLimits(1, 1024, 1, 4, 5)
    output, truncated = limits.truncate_output("abcdefgh")
    assert truncated is True
    assert "output truncated" in output


class FakeContainer:
    def __init__(self):
        self.status = "running"
        self.killed = False
        self.removed = False

    def start(self):
        return None

    def exec_run(self, command, **kwargs):
        assert command[0] == "python"
        return SimpleNamespace(exit_code=0, output=(b"hello sandbox\n", b""))

    def stop(self, **kwargs):
        self.status = "exited"

    def kill(self):
        self.killed = True

    def remove(self, **kwargs):
        self.removed = True

    def reload(self):
        return None


@pytest.mark.asyncio
async def test_manager_create_execute_destroy(tmp_path):
    manager = SandboxManager(workspace_root=tmp_path)
    container = FakeContainer()
    client = Mock()
    client.containers.create.return_value = container
    manager.docker_client = client
    container_id = await manager.create_sandbox("python")
    result = await manager.execute_code(container_id, "print('hello')", "python", 2)
    assert result["success"] is True
    assert "hello sandbox" in result["stdout"]
    assert await manager.destroy_sandbox(container_id) is True
    assert container.removed is True


@pytest.mark.asyncio
async def test_manager_requires_docker():
    manager = SandboxManager()
    with pytest.raises(RuntimeError, match="not initialized"):
        await manager.create_sandbox()


@pytest.mark.asyncio
async def test_code_executor_tools_registered():
    tools = await mcp.list_tools()
    names = {tool.name for tool in tools}
    assert {"execute_python", "execute_javascript", "execute_shell", "execute_with_data"}.issubset(names)
