"""Prompt templates for the planner/executor/coordinator agent roles."""
from __future__ import annotations

import json
from typing import Any

from .provider import Message, ToolDefinition


class PromptTemplates:
    @staticmethod
    def planner_prompt(user_goal: str, tools: list[ToolDefinition] | None = None) -> list[Message]:
        tool_text = "\n".join(f"- {tool.name}: {tool.description}" for tool in tools or []) or "No tools supplied."
        return [Message("system", "You are a planner agent. Decompose the user's goal into concrete, ordered steps. Return only JSON with steps, dependencies, expected_output, estimated_complexity, and key_risks."), Message("user", f"User goal:\n{user_goal}\n\nAvailable tools:\n{tool_text}")]

    @staticmethod
    def executor_prompt(step: dict[str, Any], context: dict[str, Any]) -> list[Message]:
        return [Message("system", "You are an executor agent. Carry out the current step using the available tools. Be precise, safe, and report the result."), Message("user", f"Step:\n{json.dumps(step, indent=2)}\n\nPrevious context:\n{json.dumps(context, indent=2, default=str)}")]

    @staticmethod
    def coordinator_prompt(user_input: str) -> list[Message]:
        return [Message("system", "You are a coordinator agent. Understand the request, decide whether planning is needed, coordinate tool use, and provide a transparent final answer."), Message("user", user_input)]

    @staticmethod
    def feedback_prompt(user_input: str, agent_output: str) -> list[Message]:
        return [Message("system", "You are reviewing feedback on an agent response. Identify what should change and propose a corrected response or plan."), Message("user", f"Agent output:\n{agent_output}\n\nUser feedback:\n{user_input}")]
