from __future__ import annotations

import pytest

from app.core.sandbox.config import SandboxConfig
from app.core.sandbox.filesystem import WorkspaceFileManager
from app.core.sandbox.security import SecurityPolicy


def test_sandbox_defaults_disable_network_and_privileges():
    config = SandboxConfig()
    policy = SecurityPolicy.from_config(config)
    assert config.network_enabled is False
    assert policy.network_disabled is True
    assert policy.no_new_privileges is True
    assert policy.cap_drop


def test_workspace_rejects_path_escape(tmp_path):
    manager = WorkspaceFileManager(tmp_path)
    with pytest.raises(ValueError):
        manager.resolve("../outside.txt")


def test_workspace_stages_and_reads_files(tmp_path):
    manager = WorkspaceFileManager(tmp_path)
    manager.write_text("input/data.txt", "hello")
    assert manager.read_text("input/data.txt") == "hello"
