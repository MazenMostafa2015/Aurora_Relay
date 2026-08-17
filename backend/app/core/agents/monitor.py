"""Progress monitoring and failure recovery policy."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..models.task import Step, StepStatus, Task, TaskStatus


class MonitorAgent:
    def __init__(self) -> None:
        self.alerts: list[dict[str, Any]] = []
        self.metrics = {"total_steps_completed": 0, "total_failures": 0, "retry_count": 0}

    async def monitor_task(self, task: Task) -> dict[str, Any]:
        completed = [step for step in task.steps if step.status == StepStatus.COMPLETED]
        failed = [step for step in task.steps if step.status == StepStatus.FAILED]
        pending = [step for step in task.steps if step.status == StepStatus.PENDING]
        durations = [(step.completed_at - step.started_at).total_seconds() for step in completed if step.started_at and step.completed_at]
        remaining = len(pending) * (sum(durations) / len(durations) if durations else 0) if pending else 0
        return {"task_id": task.id, "status": task.status.value, "progress": task.get_progress(), "total_steps": len(task.steps), "completed_steps": len(completed), "failed_steps": len(failed), "pending_steps": len(pending), "executing_steps": sum(step.status == StepStatus.EXECUTING for step in task.steps), "estimated_time_remaining": remaining or None, "alerts": self._recent_alerts(task.id), "last_updated": datetime.now(timezone.utc).isoformat()}

    async def handle_failure(self, task: Task, step: Step, error: str) -> bool:
        self.metrics["total_failures"] += 1
        self.add_alert(task.id, "error", f"Step {step.id} failed: {error}")
        if step.retry_count < step.max_retries:
            step.retry_count += 1
            step.status = StepStatus.PENDING
            self.metrics["retry_count"] += 1
            return True
        task.status = TaskStatus.FAILED
        task.error = f"Critical failure at step {step.id}: {error}"
        return False

    def add_alert(self, task_id: str, level: str, message: str) -> None:
        self.alerts.append({"task_id": task_id, "level": level, "message": message, "timestamp": datetime.now(timezone.utc).isoformat()})

    def _recent_alerts(self, task_id: str, limit: int = 5) -> list[dict[str, Any]]:
        return [alert for alert in self.alerts if alert["task_id"] == task_id][-limit:]
