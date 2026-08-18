"""Regression coverage for the frozen desktop backend runtime environment."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


BACKEND_DIRECTORY = Path(__file__).resolve().parents[2] / "backend"
sys.path.insert(0, str(BACKEND_DIRECTORY))
_specification = importlib.util.spec_from_file_location("desktop_runtime_launcher", BACKEND_DIRECTORY / "run.py")
assert _specification and _specification.loader
run = importlib.util.module_from_spec(_specification)
_specification.loader.exec_module(run)


def test_desktop_runtime_serializes_allowed_hosts_as_json(monkeypatch, tmp_path):
    """The packaged launcher must satisfy pydantic-settings complex env decoding."""
    monkeypatch.delenv("ALLOWED_HOSTS", raising=False)
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    monkeypatch.setenv("AURORA_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("AURORA_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.setenv("AURORA_LOGS_DIR", str(tmp_path / "logs"))

    run.setup_environment()

    assert json.loads(run.os.environ["ALLOWED_HOSTS"]) == ["127.0.0.1", "localhost"]
