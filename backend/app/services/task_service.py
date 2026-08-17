from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..api.models import TaskCreate, TaskStatus, TaskUpdate
from ..database.models import Step, Task


class TaskService:
    def __init__(self, db: Session, coordinator: Any = None):
        self.db = db
        self.coordinator = coordinator

    async def create_task(self, user_id: str, data: TaskCreate) -> Task:
        task = Task(user_id=user_id, order=data.order, context=data.context, status="created")
        self.db.add(task)
        self.db.commit(); self.db.refresh(task)
        if data.start_immediately and self.coordinator:
            try:
                await self.coordinator.submit_order(user_id, data.order)
                task.status = "planning"
                self.db.commit(); self.db.refresh(task)
            except Exception as exc:
                task.error = str(exc); task.status = "failed"
                self.db.commit()
        return task

    def get_task(self, task_id: str, user_id: str | None = None) -> Task | None:
        stmt = select(Task).options(selectinload(Task.steps)).where(Task.id == task_id)
        if user_id is not None: stmt = stmt.where(Task.user_id == user_id)
        return self.db.scalar(stmt)

    def list_tasks(self, user_id: str | None, status: TaskStatus | None, page: int, limit: int) -> tuple[list[Task], int]:
        stmt = select(Task).options(selectinload(Task.steps)).order_by(Task.created_at.desc())
        count = select(func.count(Task.id))
        if user_id is not None:
            stmt = stmt.where(Task.user_id == user_id); count = count.where(Task.user_id == user_id)
        if status:
            stmt = stmt.where(Task.status == status.value); count = count.where(Task.status == status.value)
        total = self.db.scalar(count) or 0
        return list(self.db.scalars(stmt.offset((page - 1) * limit).limit(limit)).all()), total

    async def update_task(self, task_id: str, user_id: str, data: TaskUpdate) -> Task | None:
        task = self.get_task(task_id, user_id)
        if not task: return None
        if data.status:
            if data.status == TaskStatus.PAUSED and self.coordinator: await self.coordinator.pause_task(task_id)
            if data.status == TaskStatus.CANCELLED and self.coordinator: await self.coordinator.cancel_task(task_id)
            task.status = data.status.value
        if data.context is not None: task.context = data.context
        task.updated_at = datetime.now(timezone.utc); self.db.commit(); self.db.refresh(task)
        return task

    def delete_task(self, task_id: str, user_id: str) -> bool:
        task = self.get_task(task_id, user_id)
        if not task: return False
        self.db.delete(task); self.db.commit(); return True

    async def status(self, task_id: str, user_id: str) -> dict[str, Any] | None:
        task = self.get_task(task_id, user_id)
        if not task: return None
        if self.coordinator:
            try: return await self.coordinator.get_task_status(task_id)
            except Exception: pass
        return {"task_id": task.id, "status": task.status, "progress": task.progress, "steps": [{"id": s.id, "status": s.status, "description": s.description} for s in task.steps]}
