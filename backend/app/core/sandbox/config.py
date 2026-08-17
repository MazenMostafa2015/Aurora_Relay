"""Configuration and policy models for isolated code execution."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SandboxLanguage(str, Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    SHELL = "shell"


class NetworkAccess(str, Enum):
    NONE = "none"
    LOCALHOST = "localhost"
    INTERNET = "internet"


@dataclass
class SandboxConfig:
    image: str = "python:3.11-slim"
    node_image: str = "node:20-slim"
    container_name_prefix: str = "sandbox-"
    timeout_seconds: int = 30
    max_timeout_seconds: int = 120
    memory_limit: str = "512m"
    cpu_limit: float = 1.0
    pids_limit: int = 128
    disk_limit: str = "100m"
    output_limit_bytes: int = 1_000_000
    read_only_rootfs: bool = True
    drop_capabilities: list[str] = field(default_factory=lambda: ["ALL"])
    add_capabilities: list[str] = field(default_factory=list)
    no_new_privileges: bool = True
    network_access: NetworkAccess = NetworkAccess.NONE
    network_mode: str = "none"
    workspace_mount: str = "/workspace"
    temp_mount: str = "/tmp"
    host_workspace: str | None = None
    allowed_mounts: list[str] = field(default_factory=list)
    enable_audit_logs: bool = True
    enable_metrics: bool = True
    alert_on_escape_attempt: bool = True
    enabled_languages: list[str] = field(default_factory=lambda: ["python", "javascript", "shell"])

    def __post_init__(self) -> None:
        self.validate()

    @property
    def network_enabled(self) -> bool:
        return self.network_access != NetworkAccess.NONE and self.network_mode != "none"

    def validate(self) -> None:
        if self.timeout_seconds <= 0 or self.timeout_seconds > self.max_timeout_seconds:
            raise ValueError("timeout_seconds must be positive and within max_timeout_seconds")
        if self.max_timeout_seconds > 600:
            raise ValueError("max_timeout_seconds may not exceed 600")
        if self.cpu_limit <= 0 or self.cpu_limit > 16:
            raise ValueError("cpu_limit must be between 0 and 16")
        if self.pids_limit <= 0 or self.pids_limit > 10000:
            raise ValueError("pids_limit must be between 1 and 10000")
        if self.output_limit_bytes <= 0 or self.output_limit_bytes > 20_000_000:
            raise ValueError("output_limit_bytes is outside the safe range")
        if self.network_access == NetworkAccess.NONE and self.network_mode != "none":
            self.network_mode = "none"
        if self.network_access == NetworkAccess.LOCALHOST and self.network_mode == "host":
            raise ValueError("host networking is not permitted for localhost policy")
        unsupported = set(self.enabled_languages) - {language.value for language in SandboxLanguage}
        if unsupported:
            raise ValueError(f"Unsupported sandbox languages: {sorted(unsupported)}")

    @staticmethod
    def parse_bytes(value: str | int) -> int:
        if isinstance(value, int):
            return value
        text = str(value).strip().lower()
        units = {"k": 1024, "kb": 1024, "m": 1024**2, "mb": 1024**2, "g": 1024**3, "gb": 1024**3}
        for suffix, multiplier in units.items():
            if text.endswith(suffix):
                return int(float(text[: -len(suffix)]) * multiplier)
        return int(text)

    def to_docker_kwargs(self, *, image: str | None = None, workspace_host: str | None = None) -> dict[str, Any]:
        self.validate()
        workspace_host = workspace_host or self.host_workspace
        mounts = {}
        if workspace_host:
            mounts[workspace_host] = {"bind": self.workspace_mount, "mode": "rw"}
        return {"image": image or self.image, "working_dir": self.workspace_mount, "detach": True, "stdin_open": False, "tty": False, "network_mode": self.network_mode, "read_only": self.read_only_rootfs, "cap_drop": list(self.drop_capabilities), "cap_add": list(self.add_capabilities), "security_opt": ["no-new-privileges:true"] if self.no_new_privileges else [], "mem_limit": self.parse_bytes(self.memory_limit), "nano_cpus": int(self.cpu_limit * 1_000_000_000), "pids_limit": self.pids_limit, "tmpfs": {self.temp_mount: f"rw,noexec,nosuid,size={self.disk_limit}"}, "volumes": mounts, "auto_remove": False}

    def to_dict(self) -> dict[str, Any]:
        return {"image": self.image, "node_image": self.node_image, "timeout_seconds": self.timeout_seconds, "max_timeout_seconds": self.max_timeout_seconds, "memory_limit": self.memory_limit, "cpu_limit": self.cpu_limit, "pids_limit": self.pids_limit, "disk_limit": self.disk_limit, "output_limit_bytes": self.output_limit_bytes, "read_only_rootfs": self.read_only_rootfs, "drop_capabilities": self.drop_capabilities, "add_capabilities": self.add_capabilities, "no_new_privileges": self.no_new_privileges, "network_access": self.network_access.value, "network_mode": self.network_mode, "workspace_mount": self.workspace_mount, "temp_mount": self.temp_mount, "host_workspace": self.host_workspace, "allowed_mounts": self.allowed_mounts, "enabled_languages": self.enabled_languages}
