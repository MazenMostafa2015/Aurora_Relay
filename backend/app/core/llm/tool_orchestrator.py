"""Bridge between the unified LLM layer and the Phase 2 MCP client."""
from __future__ import annotations

import json
from typing import Any

from mcp_servers.common.protocol import content_text

from .context import ContextManager
from .manager import LLMManager
from .provider import LLMResponse, Message, ToolDefinition


class MCPToolOrchestrator:
    def __init__(self, llm_manager: LLMManager, mcp_client: Any, context_manager: ContextManager | None = None) -> None:
        self.llm_manager = llm_manager
        self.mcp_client = mcp_client
        self.context_manager = context_manager or ContextManager()

    def tool_definitions(self) -> list[ToolDefinition]:
        definitions: list[ToolDefinition] = []
        for qualified, info in self.mcp_client.router.list_all_tools().items():
            definitions.append(ToolDefinition(name=qualified, description=info.get("description", ""), parameters=info.get("input_schema", info.get("schema", {}))))
        return definitions

    async def run(self, conversation_id: str, user_input: str, *, provider: str | None = None, max_rounds: int = 8) -> LLMResponse:
        self.context_manager.add_message(conversation_id, Message("user", user_input))
        tools = self.tool_definitions()
        for _ in range(max_rounds):
            messages = self.context_manager.get_context_messages(conversation_id)
            response = await self.llm_manager.chat_with_fallback(messages, tools, preferred_provider=provider, conversation_id=conversation_id)
            self.context_manager.add_message(conversation_id, Message("assistant", response.content, tool_calls=response.tool_calls))
            calls = response.tool_calls or []
            if not calls:
                return response
            for call in calls:
                name = call.get("name") or call.get("function", {}).get("name")
                arguments = call.get("arguments", {})
                if isinstance(arguments, str):
                    arguments = json.loads(arguments)
                result = await self.mcp_client.call_tool(name, arguments)
                self.context_manager.add_message(conversation_id, Message("tool", content_text(result), name=name, tool_call_id=call.get("id")))
        raise RuntimeError(f"Tool-calling loop exceeded max_rounds={max_rounds}")
