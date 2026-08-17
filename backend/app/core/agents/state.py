"""Task state management facade."""
from __future__ import annotations

from ..models.task import Task, TaskStatus
from ..utils.state_persistence import StatePersistence


class TaskStateManager:
    def __init__(self, persistence: StatePersistence | None = None) -> None:
        self.persistence = persistence or StatePersistence()

    def save(self, task: Task) -> None:
        task.touch()
        self.persistence.save_task(task)

    def load(self, task_id: str) -> Task | None:
        return self.persistence.load_task(task_id)

    def pause(self, task: Task) -> Task:
        task.status = TaskStatus.PAUSED
        self.save(task)
        return task

    def resume(self, task: Task) -> Task:
        if task.status == TaskStatus.PAUSED:
            task.status = TaskStatus.EXECUTING
        self.save(task)
        return task

    def cancel(self, task: Task) -> Task:
        task.status = TaskStatus.CANCELLED
        self.save(task)
        return task
