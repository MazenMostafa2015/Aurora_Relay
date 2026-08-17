"""Resource policy helpers for sandbox execution."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .config import SandboxConfig


@dataclass
class ResourceLimits:
    timeout_seconds: int
    memory_bytes: int
    nano_cpus: int
    pids_limit: int
    output_limit_bytes: int

    @classmethod
    def from_config(cls, config: SandboxConfig) -> "ResourceLimits":
        return cls(config.timeout_seconds, config.parse_bytes(config.memory_limit), int(config.cpu_limit * 1_000_000_000), config.pids_limit, config.output_limit_bytes)

    def docker_kwargs(self) -> dict[str, Any]:
        return {"mem_limit": self.memory_bytes, "nano_cpus": self.nano_cpus, "pids_limit": self.pids_limit}

    def clamp_timeout(self, requested: int | None) -> int:
        return max(1, min(int(requested or self.timeout_seconds), self.timeout_seconds))

    def truncate_output(self, text: str) -> tuple[str, bool]:
        if len(text.encode("utf-8")) <= self.output_limit_bytes:
            return text, False
        encoded = text.encode("utf-8")[: self.output_limit_bytes]
        return encoded.decode("utf-8", errors="ignore") + "\n[output truncated]", True
