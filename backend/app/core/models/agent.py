"""Agent role and runtime state models."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class AgentRole(str, Enum):
    COORDINATOR = "coordinator"
    PLANNER = "planner"
    EXECUTOR = "executor"
    MONITOR = "monitor"


@dataclass
class AgentState:
    role: AgentRole
    status: str = "idle"
    current_task_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def update(self, status: str, **metadata: Any) -> None:
        self.status = status
        self.metadata.update(metadata)
        self.updated_at = datetime.now(timezone.utc)
