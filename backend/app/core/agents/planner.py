"""Planner agent for decomposing user orders into executable steps."""
from __future__ import annotations

import logging
from typing import Any

from ..llm.prompts import PromptTemplates
from ..llm.provider import Message, ToolDefinition
from ..llm.structured import parse_json_output
from ..models.task import Step, Task, TaskStatus

logger = logging.getLogger(__name__)


class PlannerAgent:
    def __init__(self, llm_manager: Any, max_steps: int = 20) -> None:
        self.llm_manager = llm_manager
        self.max_steps = max_steps

    async def create_plan(self, task: Task, tools: list[ToolDefinition] | None = None) -> Task:
        task.status = TaskStatus.PLANNING
        response = await self.llm_manager.chat_with_fallback(PromptTemplates.planner_prompt(task.order, tools), tools=tools, conversation_id=task.id)
        data = parse_json_output(response)
        if not isinstance(data, dict):
            raise ValueError("Planner response must be a JSON object")
        steps = self._parse_steps(data, task.id)
        task.steps = self._validate_steps(steps)
        task.estimated_complexity = str(data.get("estimated_complexity", "moderate"))
        task.context["key_risks"] = data.get("key_risks", [])
        task.status = TaskStatus.PLANNED
        task.touch()
        return task

    def _parse_steps(self, plan_data: dict[str, Any], task_id: str) -> list[Step]:
        raw_steps = plan_data.get("steps", [])
        steps: list[Step] = []
        for index, raw in enumerate(raw_steps[: self.max_steps]):
            steps.append(Step(task_id=task_id, description=str(raw.get("description", f"Step {index + 1}")), order=index, tools_required=list(raw.get("tools_required", [])), dependencies=list(raw.get("dependencies", [])), input_data=dict(raw.get("input_data", {})), requires_approval=bool(raw.get("requires_approval", False)), max_retries=int(raw.get("max_retries", 3))))
        # Planner dependencies may refer to step IDs or step_# aliases. Normalize aliases.
        aliases = {f"step_{step.order + 1}": step.id for step in steps} | {str(step.order): step.id for step in steps}
        for step in steps:
            step.dependencies = [aliases.get(dep, dep) for dep in step.dependencies if aliases.get(dep, dep) in {item.id for item in steps}]
        return steps

    def _validate_steps(self, steps: list[Step]) -> list[Step]:
        ids = {step.id for step in steps}
        for step in steps:
            step.dependencies = [dependency for dependency in step.dependencies if dependency in ids and dependency != step.id]
        # Reject circular plans rather than allowing a workflow to hang indefinitely.
        visiting: set[str] = set()
        visited: set[str] = set()
        graph = {step.id: step.dependencies for step in steps}

        def visit(node: str) -> None:
            if node in visiting:
                raise ValueError("Planner produced circular step dependencies")
            if node in visited:
                return
            visiting.add(node)
            for dependency in graph[node]:
                visit(dependency)
            visiting.remove(node)
            visited.add(node)

        for node in graph:
            visit(node)
        return steps
