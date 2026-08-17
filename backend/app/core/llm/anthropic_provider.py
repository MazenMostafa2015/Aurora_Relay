"""Anthropic Messages API provider adapter."""
from __future__ import annotations

import json
from typing import Any, AsyncIterator

from .provider import LLMConfig, LLMProvider, LLMResponse, Message, ToolDefinition


class AnthropicProvider(LLMProvider):
    def __init__(self, config: LLMConfig) -> None:
        super().__init__(config)
        self.client: Any | None = None

    async def initialize(self) -> None:
        from anthropic import AsyncAnthropic

        kwargs: dict[str, Any] = {"api_key": self.config.api_key, "timeout": self.config.timeout}
        if self.config.base_url:
            kwargs["base_url"] = self.config.base_url
        self.client = AsyncAnthropic(**kwargs)
        self._initialized = True

    @staticmethod
    def _convert_messages(messages: list[Message]) -> tuple[str | None, list[dict[str, Any]]]:
        system: str | None = None
        result: list[dict[str, Any]] = []
        for message in messages:
            if message.role == "system":
                system = f"{system}\n{message.content}" if system else (message.content or "")
                continue
            role = "assistant" if message.role == "assistant" else "user"
            content: Any = message.content or ""
            if message.role == "tool":
                content = [{"type": "tool_result", "tool_use_id": message.tool_call_id or "", "content": message.content or ""}]
                role = "user"
            result.append({"role": role, "content": content})
        return system, result

    @staticmethod
    def _convert_tools(tools: list[ToolDefinition] | None) -> list[dict[str, Any]] | None:
        return [{"name": tool.name, "description": tool.description, "input_schema": tool.parameters} for tool in tools] if tools else None

    async def chat(self, messages: list[Message], tools: list[ToolDefinition] | None = None, stream: bool = False, **kwargs: Any) -> LLMResponse:
        if not self._initialized:
            await self.initialize()
        system, converted = self._convert_messages(messages)
        request: dict[str, Any] = {"model": self.config.model, "max_tokens": self.config.max_tokens, "messages": converted, "temperature": self.config.temperature, "top_p": self.config.top_p, **kwargs}
        if system:
            request["system"] = system
        tool_payload = self._convert_tools(tools)
        if tool_payload:
            request["tools"] = tool_payload
        if stream:
            request["stream"] = True
            content = []
            async with self.client.messages.stream(**request) as stream_response:
                async for text in stream_response.text_stream:
                    content.append(text)
            return LLMResponse(content="".join(content), model=self.config.model, provider=self.provider_name)
        response = await self.client.messages.create(**request)
        content_parts = [block.text for block in response.content if getattr(block, "type", None) == "text"]
        calls = []
        for block in response.content:
            if getattr(block, "type", None) == "tool_use":
                calls.append({"id": block.id, "name": block.name, "arguments": block.input, "function": {"name": block.name, "arguments": json.dumps(block.input)}})
        usage = {"prompt_tokens": response.usage.input_tokens, "completion_tokens": response.usage.output_tokens, "total_tokens": response.usage.input_tokens + response.usage.output_tokens} if response.usage else None
        return LLMResponse(content="\n".join(content_parts) or None, tool_calls=calls or None, finish_reason=response.stop_reason, usage=usage, model=response.model, provider=self.provider_name, raw=response)

    async def stream_chat(self, messages: list[Message], tools: list[ToolDefinition] | None = None, **kwargs: Any) -> AsyncIterator[str]:
        if not self._initialized:
            await self.initialize()
        system, converted = self._convert_messages(messages)
        request: dict[str, Any] = {"model": self.config.model, "max_tokens": self.config.max_tokens, "messages": converted, "temperature": self.config.temperature, "stream": True, **kwargs}
        if system:
            request["system"] = system
        tool_payload = self._convert_tools(tools)
        if tool_payload:
            request["tools"] = tool_payload
        async with self.client.messages.stream(**request) as stream_response:
            async for text in stream_response.text_stream:
                yield text
