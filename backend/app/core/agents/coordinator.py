"""Main agent coordinator and task lifecycle API."""
from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Callable
from uuid import uuid4

from ..llm.provider import ToolDefinition
from ..models.task import StepStatus, Task, TaskStatus
from ..utils.event_bus import EventBus, event_bus
from ..utils.state_persistence import StatePersistence
from .executor import ExecutorAgent
from .hitl import HumanApprovalManager
from .memory import MemoryManager
from .monitor import MonitorAgent
from .planner import PlannerAgent
from .workflow import WorkflowEngine


class Coordinator:
    def __init__(self, mcp_client: Any, llm_manager: Any, *, persistence: StatePersistence | None = None, events: EventBus | None = None, memory: MemoryManager | None = None, max_parallel: int = 4) -> None:
        self.mcp_client = mcp_client
        self.llm_manager = llm_manager
        self.persistence = persistence or StatePersistence()
        self.events = events or event_bus
        self.memory = memory or MemoryManager()
        self.planner = PlannerAgent(llm_manager)
        self.executor = ExecutorAgent(mcp_client, llm_manager)
        self.monitor = MonitorAgent()
        self.hitl = HumanApprovalManager()
        self.workflow = WorkflowEngine(max_parallel=max_parallel)
        self.tasks: dict[str, Task] = {}
        self._runs: dict[str, asyncio.Task] = {}

    async def submit_order(self, user_id: str, order: str, *, start: bool = True) -> str:
        task = Task(id=str(uuid4()), user_id=user_id, order=order)
        self.tasks[task.id] = task
        self.persistence.save_task(task)
        await self._emit("task_created", task)
        if start:
            await self._process_task(task.id)
        return task.id

    async def start_task(self, task_id: str) -> None:
        if task_id in self._runs and not self._runs[task_id].done():
            return
        task = asyncio.create_task(self._process_task(task_id))
        self._runs[task_id] = task
        await task

    async def _process_task(self, task_id: str) -> None:
        task = self.get_task(task_id)
        try:
            await self._emit("planning_started", task)
            tools = self._tool_definitions()
            task = await self.planner.create_plan(task, tools)
            self.tasks[task.id] = task
            self.persistence.save_task(task)
            await self._emit("planning_completed", task, {"steps": len(task.steps)})
            await self.workflow.run(task, self._execute_step, on_step=self._step_update)
            if task.status == TaskStatus.COMPLETED:
                task.summary = "All planned steps completed successfully."
                task.final_output = {f"step_{step.order}": step.output_data for step in task.steps}
                task.completed_at = task.updated_at
                self.memory.add_long_term(task.summary, {"task_id": task.id, "user_id": task.user_id}, importance=0.8)
                await self._emit("task_completed", task)
            elif task.status == TaskStatus.CANCELLED:
                await self._emit("task_cancelled", task)
            else:
                await self._emit("task_failed", task)
        except Exception as exc:
            task.status = TaskStatus.FAILED
            task.error = str(exc)
            task.touch()
            self.persistence.save_task(task)
            await self._emit("task_failed", task)

    async def _execute_step(self, step, context) -> Any:
        task = self.get_task(step.task_id)
        if step.requires_approval and not step.approval_given:
            await self.hitl.request_approval(task.id, step, {"order": task.order})
            task.status = TaskStatus.WAITING_FOR_INPUT
            await self._emit("approval_required", task, {"step_id": step.id, "description": step.description})
            approved = await self.hitl.wait_for_decision(task.id, step.id, timeout=3600)
            if not approved:
                step.status = StepStatus.FAILED
                step.error = "Human approval rejected"
                return step
            step.approval_given = True
            task.status = TaskStatus.EXECUTING
        await self._emit("step_started", task, {"step_id": step.id, "description": step.description, "progress": task.get_progress()})
        result = await self.executor.execute_step(step, context)
        if result.status == StepStatus.FAILED:
            recovered = await self.monitor.handle_failure(task, result, result.error or "step failed")
            if recovered:
                return await self.executor.execute_step(result, context)
        return result

    async def _step_update(self, step) -> None:
        task = self.get_task(step.task_id)
        task.touch()
        self.persistence.save_task(task)
        await self._emit("step_completed" if step.status == StepStatus.COMPLETED else "step_failed", task, {"step_id": step.id, "progress": task.get_progress(), "error": step.error})

    def _tool_definitions(self) -> list[ToolDefinition]:
        definitions = []
        for name, info in self.mcp_client.router.list_all_tools().items():
            definitions.append(ToolDefinition(name, info.get("description", ""), info.get("input_schema", info.get("schema", {}))))
        return definitions

    async def _emit(self, event_type: str, task: Task, extra: dict[str, Any] | None = None) -> None:
        self.persistence.save_task(task)
        data = {"task_id": task.id, "status": task.status.value, "progress": task.get_progress(), "order": task.order}
        if extra:
            data.update(extra)
        await self.events.emit(event_type, data)

    def get_task(self, task_id: str) -> Task:
        task = self.tasks.get(task_id)
        if not task:
            task = self.persistence.load_task(task_id)
            if task:
                self.tasks[task_id] = task
        if not task:
            raise ValueError(f"Task {task_id} not found")
        return task

    async def get_task_status(self, task_id: str) -> dict[str, Any] | None:
        try:
            return self.get_task(task_id).to_dict()
        except ValueError:
            return None

    def approve_step(self, task_id: str, step_id: str) -> None:
        self.hitl.approve(task_id, step_id)

    def reject_step(self, task_id: str, step_id: str) -> None:
        self.hitl.reject(task_id, step_id)

    def cancel_task(self, task_id: str) -> None:
        task = self.get_task(task_id)
        self.workflow.cancel(task_id)
        task.status = TaskStatus.CANCELLED
        task.touch()
        self.persistence.save_task(task)

    def add_event_listener(self, event_type: str, callback: Callable[[str, dict[str, Any]], Any]) -> None:
        self.events.subscribe(event_type, callback)

    async def stream_updates(self, task_id: str, *, poll_interval: float = 0.25) -> AsyncIterator[dict[str, Any]]:
        cursor = len(self.events.get_history(task_id=task_id, limit=1000))
        while True:
            history = self.events.get_history(task_id=task_id, limit=1000)
            for event in history[cursor:]:
                yield event
            cursor = len(history)
            status = self.get_task(task_id).status
            if status in {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED} and cursor >= len(history):
                break
            await asyncio.sleep(poll_interval)
