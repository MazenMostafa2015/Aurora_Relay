"""Executor agent for carrying out planned steps with MCP tools."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from mcp_servers.common.protocol import content_text

from ..llm.prompts import PromptTemplates
from ..llm.provider import ToolDefinition
from ..models.task import Step, StepStatus


class ExecutorAgent:
    def __init__(self, mcp_client: Any, llm_manager: Any) -> None:
        self.mcp_client = mcp_client
        self.llm_manager = llm_manager

    def _available_tools(self, step: Step) -> list[ToolDefinition]:
        inventory = self.mcp_client.router.list_all_tools()
        required = set(step.tools_required)
        definitions = []
        for name, info in inventory.items():
            if required and name not in required and name.split(":", 1)[-1] not in required:
                continue
            definitions.append(ToolDefinition(name=name, description=info.get("description", ""), parameters=info.get("input_schema", info.get("schema", {}))))
        return definitions

    async def execute_step(self, step: Step, context: dict[str, Any], *, max_rounds: int = 6) -> Step:
        step.status = StepStatus.EXECUTING
        step.started_at = datetime.now(timezone.utc)
        try:
            result = await self._execute_with_llm(step, context, max_rounds=max_rounds)
            step.output_data = result
            step.status = StepStatus.COMPLETED
            step.completed_at = datetime.now(timezone.utc)
            context[f"step_{step.order}"] = result
        except Exception as exc:
            step.error = str(exc)
            step.status = StepStatus.PENDING if step.retry_count < step.max_retries else StepStatus.FAILED
            if step.status == StepStatus.PENDING:
                step.retry_count += 1
        return step

    async def _execute_with_llm(self, step: Step, context: dict[str, Any], *, max_rounds: int) -> dict[str, Any]:
        tools = self._available_tools(step)
        messages = PromptTemplates.executor_prompt({"id": step.id, "description": step.description, "tools_required": step.tools_required}, context)
        tool_results: list[dict[str, Any]] = []
        response = None
        for _ in range(max_rounds):
            response = await self.llm_manager.chat_with_fallback(messages, tools=tools, conversation_id=step.task_id)
            messages.append(__import__("app.core.llm.provider", fromlist=["Message"]).Message("assistant", response.content, tool_calls=response.tool_calls))
            calls = response.tool_calls or []
            if not calls:
                break
            for call in calls:
                name = call.get("name") or call.get("function", {}).get("name")
                arguments = call.get("arguments", {})
                if isinstance(arguments, str):
                    arguments = json.loads(arguments)
                raw_result = await self.mcp_client.call_tool(name, arguments)
                result_text = content_text(raw_result)
                record = {"tool": name, "arguments": arguments, "result": result_text}
                step.tool_calls.append(record)
                tool_results.append(record)
                messages.append(__import__("app.core.llm.provider", fromlist=["Message"]).Message("tool", result_text, name=name, tool_call_id=call.get("id")))
        if response is None:
            raise RuntimeError("Executor received no LLM response")
        return {"summary": response.content or "", "tool_results": tool_results, "status": "success"}
