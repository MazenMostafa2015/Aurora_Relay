"""OpenAI Chat Completions provider adapter."""
from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator

from .provider import LLMConfig, LLMProvider, LLMResponse, Message, ToolDefinition

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    def __init__(self, config: LLMConfig) -> None:
        super().__init__(config)
        self.client: Any | None = None

    async def initialize(self) -> None:
        from openai import AsyncOpenAI

        kwargs: dict[str, Any] = {"api_key": self.config.api_key, "timeout": self.config.timeout}
        if self.config.base_url:
            kwargs["base_url"] = self.config.base_url
        self.client = AsyncOpenAI(**kwargs)
        self._initialized = True
        logger.info("Initialized OpenAI provider with model %s", self.config.model)

    def _messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        return [message.to_dict() for message in messages]

    def _tools(self, tools: list[ToolDefinition] | None) -> list[dict[str, Any]] | None:
        return [tool.to_openai() for tool in tools] if tools else None

    async def chat(self, messages: list[Message], tools: list[ToolDefinition] | None = None, stream: bool = False, **kwargs: Any) -> LLMResponse:
        if not self._initialized:
            await self.initialize()
        request = {
            "model": self.config.model,
            "messages": self._messages(messages),
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "top_p": self.config.top_p,
            "frequency_penalty": self.config.frequency_penalty,
            "presence_penalty": self.config.presence_penalty,
            "stream": stream,
            **kwargs,
        }
        tool_payload = self._tools(tools)
        if tool_payload:
            request["tools"] = tool_payload
        response = await self.client.chat.completions.create(**request)
        if stream:
            content: list[str] = []
            async for chunk in response:
                delta = chunk.choices[0].delta
                if delta.content:
                    content.append(delta.content)
            return LLMResponse(content="".join(content), model=self.config.model, provider=self.provider_name)
        choice = response.choices[0]
        message = choice.message
        tool_calls = self._normalize_tool_calls(getattr(message, "tool_calls", None))
        usage = None
        if response.usage:
            usage = {"prompt_tokens": response.usage.prompt_tokens, "completion_tokens": response.usage.completion_tokens, "total_tokens": response.usage.total_tokens}
        return LLMResponse(content=message.content, tool_calls=tool_calls, finish_reason=choice.finish_reason, usage=usage, model=response.model, provider=self.provider_name, raw=response)

    async def stream_chat(self, messages: list[Message], tools: list[ToolDefinition] | None = None, **kwargs: Any) -> AsyncIterator[str]:
        if not self._initialized:
            await self.initialize()
        request = {"model": self.config.model, "messages": self._messages(messages), "temperature": self.config.temperature, "max_tokens": self.config.max_tokens, "stream": True, **kwargs}
        tool_payload = self._tools(tools)
        if tool_payload:
            request["tools"] = tool_payload
        response = await self.client.chat.completions.create(**request)
        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    @staticmethod
    def _normalize_tool_calls(tool_calls: Any) -> list[dict[str, Any]] | None:
        if not tool_calls:
            return None
        normalized = []
        for call in tool_calls:
            function = getattr(call, "function", None)
            raw_args = getattr(function, "arguments", "{}") if function else "{}"
            try:
                arguments = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            except json.JSONDecodeError:
                arguments = {"_raw": raw_args}
            normalized.append({"id": getattr(call, "id", None), "name": getattr(function, "name", "") if function else "", "arguments": arguments, "function": {"name": getattr(function, "name", "") if function else "", "arguments": raw_args}})
        return normalized
