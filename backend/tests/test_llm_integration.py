from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from app.core.llm import (
    ContextManager,
    CostTracker,
    LLMConfig,
    LLMManager,
    LLMResponse,
    Message,
    ModelProvider,
    ResponseCache,
    ToolDefinition,
    parse_json_output,
)
from app.core.llm.ollama_provider import OllamaProvider
from app.core.llm.provider import LLMProvider
from app.core.llm.structured import StructuredOutputError


def test_message_and_tool_serialization():
    message = Message("assistant", "done", tool_calls=[{"id": "1"}])
    tool = ToolDefinition("read", "Read a file", {"type": "object"})
    assert message.to_dict()["tool_calls"] == [{"id": "1"}]
    assert tool.to_openai()["function"]["name"] == "read"


def test_context_preserves_system_and_truncates():
    manager = ContextManager(max_tokens=8)
    manager.add_message("c", Message("system", "system prompt"))
    manager.add_message("c", Message("user", "x" * 40))
    messages = manager.get_context_messages("c")
    assert messages[0].role == "system"
    assert manager.get_or_create_context("c").token_count <= 8


def test_cache_key_and_ttl():
    cache = ResponseCache(ttl=60)
    key = cache.make_key("local", [Message("user", "hello")], None, {})
    response = LLMResponse(content="world")
    cache.set(key, response)
    assert cache.get(key).content == "world"
    assert cache.stats()["hits"] == 1


def test_structured_output_parsing_and_validation():
    schema = {"type": "object", "required": ["answer"], "properties": {"answer": {"type": "string"}}}
    assert parse_json_output("```json\n{\"answer\": \"ok\"}\n```", schema)["answer"] == "ok"
    with pytest.raises(StructuredOutputError):
        parse_json_output("not json")


def test_cost_tracker_ollama_is_zero_cost():
    tracker = CostTracker()
    provider = SimpleNamespace(provider_name="ollama", get_model_name=lambda: "phi3:mini")
    entry = tracker.record(provider, LLMResponse(usage={"prompt_tokens": 10, "completion_tokens": 5}, model="phi3:mini"))
    assert entry.cost == 0
    assert tracker.summary()["total_tokens"] == 15


def test_manager_registers_and_switches_providers():
    manager = LLMManager()
    manager.register_provider("local", LLMConfig(ModelProvider.OLLAMA, "phi3:mini"))
    manager.register_provider("cloud", LLMConfig(ModelProvider.OPENAI, "gpt-4o-mini", api_key="test"))
    assert manager.default_provider == "local"
    assert manager.switch_provider("cloud").config.model == "gpt-4o-mini"


@pytest.mark.asyncio
async def test_manager_fallback(monkeypatch):
    manager = LLMManager()
    manager.register_provider("bad", LLMConfig(ModelProvider.OLLAMA, "bad"))
    manager.register_provider("good", LLMConfig(ModelProvider.OLLAMA, "good"))

    async def fail(*args, **kwargs):
        raise RuntimeError("offline")

    async def succeed(*args, **kwargs):
        return LLMResponse(content="ok", model="good")

    monkeypatch.setattr(manager.providers["bad"], "chat", fail)
    monkeypatch.setattr(manager.providers["good"], "chat", succeed)
    result = await manager.chat_with_fallback([Message("user", "hi")])
    assert result.content == "ok"


@pytest.mark.asyncio
async def test_ollama_response_normalization():
    provider = OllamaProvider(LLMConfig(ModelProvider.OLLAMA, "phi3:mini"))
    provider._initialized = True
    provider.client = SimpleNamespace()

    class FakeResponse:
        def raise_for_status(self):
            return None
        def json(self):
            return {"model": "phi3:mini", "done": True, "message": {"content": "hi", "tool_calls": [{"function": {"name": "read", "arguments": {"path": "."}}}]}, "prompt_eval_count": 2, "eval_count": 3}

    async def post(*args, **kwargs):
        return FakeResponse()

    provider.client.post = post
    result = await provider.chat([Message("user", "hi")])
    assert result.content == "hi"
    assert result.tool_calls[0]["name"] == "read"
    assert result.usage["total_tokens"] == 5


@pytest.mark.asyncio
async def test_streaming_provider_contract():
    class FakeProvider(LLMProvider):
        async def initialize(self):
            self._initialized = True
        async def chat(self, messages, tools=None, stream=False, **kwargs):
            return LLMResponse(content="full")
        async def stream_chat(self, messages, tools=None, **kwargs):
            yield "a"
            yield "b"

    provider = FakeProvider(LLMConfig(ModelProvider.OLLAMA, "local"))
    assert [chunk async for chunk in provider.stream_chat([Message("user", "x")])] == ["a", "b"]
