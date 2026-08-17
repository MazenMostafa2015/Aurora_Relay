"""Core task and step state models for the agent orchestrator."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


def now() -> datetime:
    return datetime.now(timezone.utc)


class TaskStatus(str, Enum):
    CREATED = "created"
    PLANNING = "planning"
    PLANNED = "planned"
    EXECUTING = "executing"
    PAUSED = "paused"
    WAITING_FOR_INPUT = "waiting_for_input"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WAITING_APPROVAL = "waiting_approval"


@dataclass
class Step:
    id: str = field(default_factory=lambda: str(uuid4()))
    task_id: str = ""
    description: str = ""
    order: int = 0
    status: StepStatus = StepStatus.PENDING
    tools_required: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    depends_on: list[str] | None = None
    input_data: dict[str, Any] = field(default_factory=dict)
    output_data: dict[str, Any] | None = None
    error: str | None = None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    retry_count: int = 0
    max_retries: int = 3
    requires_approval: bool = False
    approval_given: bool = False

    def __post_init__(self) -> None:
        if self.depends_on is not None:
            self.dependencies = list(self.depends_on)

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "task_id": self.task_id, "description": self.description, "order": self.order, "status": self.status.value, "tools_required": self.tools_required, "dependencies": self.dependencies, "input_data": self.input_data, "output_data": self.output_data, "error": self.error, "tool_calls": self.tool_calls, "created_at": self.created_at.isoformat(), "started_at": self.started_at.isoformat() if self.started_at else None, "completed_at": self.completed_at.isoformat() if self.completed_at else None, "retry_count": self.retry_count, "max_retries": self.max_retries, "requires_approval": self.requires_approval, "approval_given": self.approval_given}


@dataclass
class Task:
    id: str = field(default_factory=lambda: str(uuid4()))
    user_id: str = ""
    order: str = ""
    status: TaskStatus = TaskStatus.CREATED
    steps: list[Step] = field(default_factory=list)
    current_step_index: int = 0
    summary: str | None = None
    final_output: dict[str, Any] | None = None
    error: str | None = None
    context: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=now)
    updated_at: datetime = field(default_factory=now)
    completed_at: datetime | None = None
    estimated_complexity: str = "moderate"

    def get_pending_steps(self) -> list[Step]:
        return [step for step in self.steps if step.status == StepStatus.PENDING]

    def get_next_step(self) -> Step | None:
        completed = {step.id for step in self.steps if step.status == StepStatus.COMPLETED}
        for step in sorted(self.steps, key=lambda item: item.order):
            if step.status == StepStatus.PENDING and all(dep in completed for dep in step.dependencies):
                return step
        return None

    def get_progress(self) -> float:
        return 0.0 if not self.steps else sum(step.status == StepStatus.COMPLETED for step in self.steps) / len(self.steps) * 100

    def touch(self) -> None:
        self.updated_at = now()

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "user_id": self.user_id, "order": self.order, "status": self.status.value, "steps": [step.to_dict() for step in self.steps], "current_step_index": self.current_step_index, "summary": self.summary, "final_output": self.final_output, "error": self.error, "context": self.context, "created_at": self.created_at.isoformat(), "updated_at": self.updated_at.isoformat(), "completed_at": self.completed_at.isoformat() if self.completed_at else None, "estimated_complexity": self.estimated_complexity, "progress": self.get_progress()}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Task":
        task = cls(id=data["id"], user_id=data.get("user_id", ""), order=data.get("order", ""), status=TaskStatus(data.get("status", TaskStatus.CREATED.value)), current_step_index=int(data.get("current_step_index", 0)), summary=data.get("summary"), final_output=data.get("final_output"), error=data.get("error"), context=data.get("context", {}), estimated_complexity=data.get("estimated_complexity", "moderate"))
        task.steps = [Step(id=item["id"], task_id=item.get("task_id", task.id), description=item.get("description", ""), order=item.get("order", 0), status=StepStatus(item.get("status", StepStatus.PENDING.value)), tools_required=item.get("tools_required", []), dependencies=item.get("dependencies", []), input_data=item.get("input_data", {}), output_data=item.get("output_data"), error=item.get("error"), tool_calls=item.get("tool_calls", []), retry_count=item.get("retry_count", 0), max_retries=item.get("max_retries", 3), requires_approval=item.get("requires_approval", False), approval_given=item.get("approval_given", False)) for item in data.get("steps", [])]
        return task
