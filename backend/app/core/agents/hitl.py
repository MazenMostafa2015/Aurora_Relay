"""Human approval gate for sensitive agent steps."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from ..models.task import Step, StepStatus


@dataclass
class ApprovalRequest:
    task_id: str
    step_id: str
    description: str
    metadata: dict[str, Any]
    decision: bool | None = None


class HumanApprovalManager:
    def __init__(self) -> None:
        self.pending: dict[tuple[str, str], ApprovalRequest] = {}
        self._events: dict[tuple[str, str], asyncio.Event] = {}

    async def request_approval(self, task_id: str, step: Step, metadata: dict[str, Any] | None = None) -> ApprovalRequest:
        key = (task_id, step.id)
        request = ApprovalRequest(task_id, step.id, step.description, metadata or {})
        self.pending[key] = request
        self._events.setdefault(key, asyncio.Event())
        step.status = StepStatus.WAITING_APPROVAL
        return request

    def decide(self, task_id: str, step_id: str, approved: bool) -> None:
        key = (task_id, step_id)
        if key not in self.pending:
            raise KeyError(f"No pending approval for {task_id}/{step_id}")
        self.pending[key].decision = approved
        self._events.setdefault(key, asyncio.Event()).set()

    async def wait_for_decision(self, task_id: str, step_id: str, timeout: float | None = None) -> bool:
        key = (task_id, step_id)
        request = self.pending.get(key)
        if not request:
            raise KeyError(f"No pending approval for {task_id}/{step_id}")
        event = self._events.setdefault(key, asyncio.Event())
        if request.decision is None:
            if timeout is None:
                await event.wait()
            else:
                await asyncio.wait_for(event.wait(), timeout)
        decision = bool(request.decision)
        self.pending.pop(key, None)
        self._events.pop(key, None)
        return decision

    def approve(self, task_id: str, step_id: str) -> None:
        self.decide(task_id, step_id, True)

    def reject(self, task_id: str, step_id: str) -> None:
        self.decide(task_id, step_id, False)
