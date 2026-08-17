"""Local Ollama provider adapter using the Ollama HTTP API."""
from __future__ import annotations

import json
from typing import Any, AsyncIterator

import httpx

from .provider import LLMConfig, LLMProvider, LLMResponse, Message, ToolDefinition


class OllamaProvider(LLMProvider):
    def __init__(self, config: LLMConfig) -> None:
        super().__init__(config)
        self.base_url = (config.base_url or "http://localhost:11434").rstrip("/")
        self.client: httpx.AsyncClient | None = None

    async def initialize(self) -> None:
        self.client = httpx.AsyncClient(timeout=self.config.timeout)
        response = await self.client.get(f"{self.base_url}/api/tags")
        response.raise_for_status()
        models = response.json().get("models", [])
        available = {item.get("name") for item in models}
        if available and self.config.model not in available:
            raise RuntimeError(f"Ollama model '{self.config.model}' is not installed; available models: {sorted(available)}")
        self._initialized = True

    @staticmethod
    def _tools(tools: list[ToolDefinition] | None) -> list[dict[str, Any]] | None:
        if not tools:
            return None
        return [{"type": "function", "function": {"name": tool.name, "description": tool.description, "parameters": tool.parameters}} for tool in tools]

    async def chat(self, messages: list[Message], tools: list[ToolDefinition] | None = None, stream: bool = False, **kwargs: Any) -> LLMResponse:
        if not self._initialized:
            await self.initialize()
        payload: dict[str, Any] = {"model": self.config.model, "messages": [message.to_dict() for message in messages], "stream": stream, "options": {"temperature": self.config.temperature, "top_p": self.config.top_p}, **kwargs}
        tool_payload = self._tools(tools)
        if tool_payload:
            payload["tools"] = tool_payload
        response = await self.client.post(f"{self.base_url}/api/chat", json=payload)
        response.raise_for_status()
        if stream:
            content: list[str] = []
            calls: list[dict[str, Any]] = []
            for line in response.text.splitlines():
                if not line.strip():
                    continue
                item = json.loads(line)
                message = item.get("message", {})
                content.append(message.get("content", ""))
                calls.extend(self._normalize_tool_calls(message.get("tool_calls")))
            return LLMResponse(content="".join(content) or None, tool_calls=calls or None, model=self.config.model, provider=self.provider_name, raw=response)
        item = response.json()
        message = item.get("message", {})
        calls = self._normalize_tool_calls(message.get("tool_calls"))
        usage = {"prompt_tokens": item["prompt_eval_count"], "completion_tokens": item["eval_count"], "total_tokens": item["prompt_eval_count"] + item["eval_count"]} if "prompt_eval_count" in item and "eval_count" in item else None
        return LLMResponse(content=message.get("content") or None, tool_calls=calls or None, finish_reason="stop" if item.get("done") else None, usage=usage, model=item.get("model", self.config.model), provider=self.provider_name, raw=item)

    async def stream_chat(self, messages: list[Message], tools: list[ToolDefinition] | None = None, **kwargs: Any) -> AsyncIterator[str]:
        if not self._initialized:
            await self.initialize()
        payload: dict[str, Any] = {"model": self.config.model, "messages": [message.to_dict() for message in messages], "stream": True, "options": {"temperature": self.config.temperature, "top_p": self.config.top_p}, **kwargs}
        tool_payload = self._tools(tools)
        if tool_payload:
            payload["tools"] = tool_payload
        async with self.client.stream("POST", f"{self.base_url}/api/chat", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                item = json.loads(line)
                text = item.get("message", {}).get("content", "")
                if text:
                    yield text

    @staticmethod
    def _normalize_tool_calls(raw_calls: Any) -> list[dict[str, Any]]:
        calls = []
        for index, call in enumerate(raw_calls or []):
            function = call.get("function", call) if isinstance(call, dict) else {}
            name = function.get("name", "")
            arguments = function.get("arguments", {})
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    arguments = {"_raw": arguments}
            calls.append({"id": call.get("id", f"ollama_call_{index}"), "name": name, "arguments": arguments, "function": {"name": name, "arguments": json.dumps(arguments)}})
        return calls
