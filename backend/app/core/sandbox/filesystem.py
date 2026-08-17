"""Safe workspace staging and file access for sandbox containers."""
from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Any


class SandboxFilesystem:
    def __init__(self, workspace_root: str | Path = "workspace", max_file_bytes: int = 10_000_000) -> None:
        self.workspace_root = Path(workspace_root).resolve()
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self.max_file_bytes = max_file_bytes

    def safe_path(self, relative_path: str) -> Path:
        candidate = (self.workspace_root / relative_path).resolve()
        if candidate != self.workspace_root and self.workspace_root not in candidate.parents:
            raise PermissionError("Path escapes the sandbox workspace")
        return candidate

    def stage_files(self, files: dict[str, str | bytes] | None) -> Path:
        directory = Path(tempfile.mkdtemp(prefix="sandbox-", dir=self.workspace_root))
        for name, content in (files or {}).items():
            path = (directory / name).resolve()
            if directory not in path.parents:
                shutil.rmtree(directory, ignore_errors=True)
                raise PermissionError("Workspace file path escapes its staging directory")
            path.parent.mkdir(parents=True, exist_ok=True)
            data = content.encode() if isinstance(content, str) else content
            if len(data) > self.max_file_bytes:
                shutil.rmtree(directory, ignore_errors=True)
                raise ValueError(f"Input file exceeds {self.max_file_bytes} bytes")
            path.write_bytes(data)
        return directory

    def read_files(self, directory: str | Path) -> dict[str, str]:
        root = Path(directory).resolve()
        if self.workspace_root not in root.parents and root != self.workspace_root:
            raise PermissionError("Cannot read outside workspace")
        result: dict[str, str] = {}
        for path in root.rglob("*"):
            if path.is_file() and path.stat().st_size <= self.max_file_bytes:
                result[str(path.relative_to(root))] = path.read_text(errors="replace")
        return result

    def cleanup(self, directory: str | Path) -> None:
        path = Path(directory).resolve()
        if self.workspace_root not in path.parents:
            raise PermissionError("Cannot clean outside workspace")
        shutil.rmtree(path, ignore_errors=True)


class WorkspaceFileManager(SandboxFilesystem):
    """Compatibility facade for safe per-file workspace operations."""

    def resolve(self, relative_path: str) -> Path:
        try:
            return self.safe_path(relative_path)
        except PermissionError as exc:
            raise ValueError(str(exc)) from exc

    def write_text(self, relative_path: str, content: str) -> Path:
        path = self.resolve(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = content.encode()
        if len(data) > self.max_file_bytes:
            raise ValueError(f"Input file exceeds {self.max_file_bytes} bytes")
        path.write_text(content)
        return path

    def read_text(self, relative_path: str) -> str:
        path = self.resolve(relative_path)
        return path.read_text()
