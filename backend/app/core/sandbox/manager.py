"""Docker-backed lifecycle manager for isolated code execution.

The Docker SDK is imported lazily so the application can still start and expose
clear configuration errors on hosts where Docker is unavailable.
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from pathlib import Path
from typing import Any

from .config import SandboxConfig, SandboxLanguage
from .filesystem import SandboxFilesystem
from .monitor import SandboxMonitor
from .resources import ResourceLimits
from .security import SecurityHardener

logger = logging.getLogger(__name__)


class SandboxManager:
    def __init__(self, config: SandboxConfig | None = None, *, workspace_root: str | Path = "workspace") -> None:
        self.config = config or SandboxConfig()
        self.docker_client: Any = None
        self.active_containers: dict[str, Any] = {}
        self.staged_workspaces: dict[str, Path] = {}
        self.execution_history: list[dict[str, Any]] = []
        self.security = SecurityHardener()
        self.resources = ResourceLimits.from_config(self.config)
        self.filesystem = SandboxFilesystem(workspace_root)
        self.monitor = SandboxMonitor()

    async def initialize(self) -> None:
        try:
            import docker  # type: ignore
        except ImportError as exc:
            raise RuntimeError("Docker Python SDK is not installed. Install the project requirements or use a Docker-enabled deployment.") from exc
        try:
            self.docker_client = await asyncio.to_thread(docker.from_env)
            await asyncio.to_thread(self.docker_client.ping)
        except Exception as exc:
            self.docker_client = None
            raise RuntimeError("Docker is not available. Start Docker or use the mock execution tests.") from exc

    def _get_image_for_language(self, language: str) -> str:
        if language == SandboxLanguage.PYTHON.value:
            return self.config.image
        if language == SandboxLanguage.JAVASCRIPT.value:
            return self.config.node_image
        if language == SandboxLanguage.SHELL.value:
            return self.config.image
        raise ValueError(f"Unsupported sandbox language: {language}")

    def _get_execution_command(self, language: str, filename: str) -> list[str]:
        if language == SandboxLanguage.PYTHON.value:
            return ["python", filename]
        if language == SandboxLanguage.JAVASCRIPT.value:
            return ["node", filename]
        if language == SandboxLanguage.SHELL.value:
            return ["sh", filename]
        raise ValueError(f"Unsupported sandbox language: {language}")

    async def create_sandbox(self, language: str = "python", workspace_files: dict[str, str | bytes] | None = None, config: SandboxConfig | None = None) -> str:
        if not self.docker_client:
            raise RuntimeError("Sandbox manager is not initialized or Docker is unavailable")
        config = config or self.config
        config.validate()
        if language not in config.enabled_languages:
            raise ValueError(f"Language '{language}' is disabled")
        container_id = f"{config.container_name_prefix}{uuid.uuid4().hex[:12]}"
        workspace = await asyncio.to_thread(self.filesystem.stage_files, workspace_files)
        kwargs = config.to_docker_kwargs(image=self._get_image_for_language(language), workspace_host=str(workspace))
        kwargs.update({"name": container_id, "command": ["sh", "-c", "sleep infinity"]})
        try:
            container = await asyncio.to_thread(self.docker_client.containers.create, **kwargs)
            await asyncio.to_thread(container.start)
            self.active_containers[container_id] = container
            self.staged_workspaces[container_id] = workspace
            return container_id
        except Exception:
            self.filesystem.cleanup(workspace)
            raise

    async def execute_code(self, container_id: str, code: str, language: str = "python", timeout: int | None = None) -> dict[str, Any]:
        container = self.active_containers.get(container_id)
        if not container:
            raise ValueError(f"Container {container_id} not found")
        if self.security.inspect_command(code):
            self.security.detect_escape_attempt(container_id, "suspicious execution content")
        timeout_seconds = self.resources.clamp_timeout(timeout)
        filename = {"python": "main.py", "javascript": "main.js", "shell": "main.sh"}.get(language)
        if not filename:
            raise ValueError(f"Unsupported sandbox language: {language}")
        workspace = self.staged_workspaces[container_id]
        (workspace / filename).write_text(code, encoding="utf-8")
        command = self._get_execution_command(language, f"{self.config.workspace_mount}/{filename}")
        execution_id = uuid.uuid4().hex
        self.monitor.start_monitoring(execution_id, container_id)
        started = time.monotonic()
        try:
            result = await asyncio.wait_for(asyncio.to_thread(container.exec_run, command, workdir=self.config.workspace_mount, demux=True), timeout=timeout_seconds)
            stdout, stderr = self._decode_output(getattr(result, "output", None))
            stdout, stdout_truncated = self.resources.truncate_output(stdout)
            stderr, stderr_truncated = self.resources.truncate_output(stderr)
            exit_code = int(getattr(result, "exit_code", -1))
            metrics = self.monitor.stop_monitoring(execution_id, success=exit_code == 0, exit_code=exit_code)
            record = {"success": exit_code == 0, "exit_code": exit_code, "stdout": stdout, "stderr": stderr, "execution_time": time.monotonic() - started, "language": language, "timed_out": False, "output_truncated": stdout_truncated or stderr_truncated, "metrics": metrics}
        except asyncio.TimeoutError:
            await asyncio.to_thread(container.kill)
            metrics = self.monitor.stop_monitoring(execution_id, success=False, exit_code=-9)
            record = {"success": False, "exit_code": -9, "stdout": "", "stderr": "Execution timed out", "execution_time": time.monotonic() - started, "language": language, "timed_out": True, "output_truncated": False, "metrics": metrics}
        except Exception as exc:
            metrics = self.monitor.stop_monitoring(execution_id, success=False, exit_code=-1)
            record = {"success": False, "exit_code": -1, "stdout": "", "stderr": str(exc), "execution_time": time.monotonic() - started, "language": language, "timed_out": False, "output_truncated": False, "metrics": metrics}
        self.execution_history.append({"container_id": container_id, **record})
        return record

    @staticmethod
    def _decode_output(output: Any) -> tuple[str, str]:
        if output is None:
            return "", ""
        if isinstance(output, tuple):
            first, second = output
            return (first or b"").decode(errors="replace") if isinstance(first, bytes) else str(first or ""), (second or b"").decode(errors="replace") if isinstance(second, bytes) else str(second or "")
        if isinstance(output, bytes):
            return output.decode(errors="replace"), ""
        return str(output), ""

    async def destroy_sandbox(self, container_id: str) -> bool:
        container = self.active_containers.pop(container_id, None)
        workspace = self.staged_workspaces.pop(container_id, None)
        if not container:
            if workspace:
                self.filesystem.cleanup(workspace)
            return False
        try:
            await asyncio.to_thread(container.stop, timeout=2)
        except Exception:
            try:
                await asyncio.to_thread(container.kill)
            except Exception:
                pass
        try:
            await asyncio.to_thread(container.remove, force=True)
        except Exception:
            pass
        if workspace:
            self.filesystem.cleanup(workspace)
        return True

    async def cleanup_all(self) -> None:
        await asyncio.gather(*(self.destroy_sandbox(container_id) for container_id in list(self.active_containers)), return_exceptions=True)

    async def get_container_status(self, container_id: str) -> dict[str, Any] | None:
        container = self.active_containers.get(container_id)
        if not container:
            return None
        await asyncio.to_thread(container.reload)
        return {"id": container_id, "status": getattr(container, "status", None), "image": getattr(getattr(container, "image", None), "tags", [])}
