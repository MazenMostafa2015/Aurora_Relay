"""Dependency-aware workflow scheduler for task steps."""
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from ..models.task import Step, StepStatus, Task, TaskStatus


class WorkflowEngine:
    def __init__(self, max_parallel: int = 4, max_concurrency: int | None = None) -> None:
        self.max_parallel = max_concurrency if max_concurrency is not None else max_parallel
        self._cancelled: set[str] = set()

    def cancel(self, task_id: str) -> None:
        self._cancelled.add(task_id)

    async def run(self, task: Task | list[Step], execute_step: Callable[..., Awaitable[Any]], *, on_step: Callable[[Step], Awaitable[None]] | None = None) -> Task | dict[str, str]:
        if isinstance(task, list):
            completed: set[str] = set()
            pending = list(task)
            while pending:
                ready = [step for step in pending if all(dep in completed for dep in step.dependencies)]
                if not ready:
                    raise RuntimeError("Workflow is blocked by unresolved dependencies")
                for step in ready[: self.max_parallel]:
                    result = await execute_step(step)
                    if isinstance(result, Exception):
                        step.error = str(result)
                        step.status = StepStatus.FAILED
                        return {"status": "failed"}
                    step.status = StepStatus.COMPLETED
                    completed.add(step.id)
                    pending.remove(step)
            return {"status": "completed"}
        task.status = TaskStatus.EXECUTING
        while True:
            if task.id in self._cancelled:
                task.status = TaskStatus.CANCELLED
                break
            ready = [step for step in task.steps if step.status == StepStatus.PENDING and all(any(dep.id == dependency and dep.status == StepStatus.COMPLETED for dep in task.steps) for dependency in step.dependencies)]
            if not ready:
                if all(step.status in {StepStatus.COMPLETED, StepStatus.SKIPPED} for step in task.steps):
                    task.status = TaskStatus.COMPLETED
                elif any(step.status == StepStatus.FAILED for step in task.steps):
                    task.status = TaskStatus.FAILED
                elif any(step.status == StepStatus.WAITING_APPROVAL for step in task.steps):
                    task.status = TaskStatus.WAITING_FOR_INPUT
                elif task.steps:
                    raise RuntimeError("Workflow is blocked by unresolved dependencies")
                break
            batch = ready[: self.max_parallel]
            results = await asyncio.gather(*(execute_step(step, task.context) for step in batch), return_exceptions=True)
            for step, result in zip(batch, results):
                if isinstance(result, Exception):
                    step.error = str(result)
                    step.status = StepStatus.FAILED
                if on_step:
                    await on_step(step)
                if step.status == StepStatus.FAILED:
                    task.status = TaskStatus.FAILED
                    task.error = step.error or f"Step {step.id} failed"
                    return task
            task.current_step_index = min(len(task.steps), task.current_step_index + len(batch))
            task.touch()
        task.touch()
        return task
