"""Execution monitoring and audit metrics."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class ExecutionMetric:
    execution_id: str
    container_id: str | None
    started_at: datetime
    ended_at: datetime | None = None
    success: bool | None = None
    exit_code: int | None = None
    memory_samples_mb: list[float] = field(default_factory=list)
    cpu_samples_percent: list[float] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        duration = (self.ended_at - self.started_at).total_seconds() if self.ended_at else None
        return {"execution_id": self.execution_id, "container_id": self.container_id, "started_at": self.started_at.isoformat(), "ended_at": self.ended_at.isoformat() if self.ended_at else None, "duration": duration, "success": self.success, "exit_code": self.exit_code, "peak_memory_mb": max(self.memory_samples_mb, default=0), "avg_cpu_percent": sum(self.cpu_samples_percent) / len(self.cpu_samples_percent) if self.cpu_samples_percent else 0}


class SandboxMonitor:
    def __init__(self) -> None:
        self.active: dict[str, ExecutionMetric] = {}
        self.completed: list[ExecutionMetric] = []

    def start_monitoring(self, execution_id: str, container_id: str | None = None) -> None:
        self.active[execution_id] = ExecutionMetric(execution_id, container_id, datetime.now(timezone.utc))

    def sample(self, execution_id: str, memory_mb: float = 0, cpu_percent: float = 0) -> None:
        if execution_id in self.active:
            self.active[execution_id].memory_samples_mb.append(memory_mb)
            self.active[execution_id].cpu_samples_percent.append(cpu_percent)

    def stop_monitoring(self, execution_id: str, *, success: bool, exit_code: int) -> dict[str, Any]:
        metric = self.active.pop(execution_id, None)
        if not metric:
            return {}
        metric.ended_at = datetime.now(timezone.utc)
        metric.success = success
        metric.exit_code = exit_code
        self.completed.append(metric)
        return metric.to_dict()

    def get_global_metrics(self) -> dict[str, Any]:
        total = len(self.completed)
        durations = [item.to_dict()["duration"] for item in self.completed if item.ended_at]
        return {"total_executions": total, "failed_executions": sum(item.success is False for item in self.completed), "success_rate": ((sum(item.success is True for item in self.completed) / total) * 100) if total else 0, "avg_execution_time": sum(durations) / len(durations) if durations else 0, "peak_memory_usage_mb": max((max(item.memory_samples_mb, default=0) for item in self.completed), default=0)}
