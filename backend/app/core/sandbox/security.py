"""Security policy helpers for Docker sandboxes."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .config import SandboxConfig


class SecurityHardener:
    def __init__(self) -> None:
        self.detected_escape_attempts: list[dict[str, Any]] = []

    def docker_security_kwargs(self, config: SandboxConfig) -> dict[str, Any]:
        return {"cap_drop": list(config.drop_capabilities), "cap_add": list(config.add_capabilities), "security_opt": ["no-new-privileges:true"] if config.no_new_privileges else [], "read_only": config.read_only_rootfs, "privileged": False, "pid_mode": None, "ipc_mode": None, "uts_mode": None}

    def inspect_command(self, command: str) -> list[str]:
        suspicious = ["/var/run/docker.sock", "nsenter", "--privileged", "mount -t", "unshare", "setns", "ptrace", "\x00"]
        return [pattern for pattern in suspicious if pattern in command]

    def detect_escape_attempt(self, container_id: str, event: str) -> dict[str, Any]:
        record = {"container_id": container_id, "event": event, "timestamp": datetime.now(timezone.utc).isoformat()}
        self.detected_escape_attempts.append(record)
        return record

    def audit_snapshot(self) -> list[dict[str, Any]]:
        return list(self.detected_escape_attempts)


class SecurityPolicy:
    """Read-only summary of the sandbox controls enforced by configuration."""

    def __init__(self, *, network_disabled: bool, no_new_privileges: bool, cap_drop: list[str]) -> None:
        self.network_disabled = network_disabled
        self.no_new_privileges = no_new_privileges
        self.cap_drop = cap_drop

    @classmethod
    def from_config(cls, config: SandboxConfig) -> "SecurityPolicy":
        config.validate()
        return cls(
            network_disabled=config.network_access.value == "none" or config.network_mode == "none",
            no_new_privileges=config.no_new_privileges,
            cap_drop=list(config.drop_capabilities),
        )
