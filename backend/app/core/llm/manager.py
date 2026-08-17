"""Provider registry and fallback orchestration."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from .anthropic_provider import AnthropicProvider
from .cache import ResponseCache
from .cost_tracker import CostTracker
from .ollama_provider import OllamaProvider
from .openai_provider import OpenAIProvider
from .provider import LLMConfig, LLMProvider, LLMResponse, Message, ModelProvider, ToolDefinition

logger = logging.getLogger(__name__)


class LLMManager:
    def __init__(self, *, cache: ResponseCache | None = None, cost_tracker: CostTracker | None = None) -> None:
        self.providers: dict[str, LLMProvider] = {}
        self.default_provider: str | None = None
        self.cache = cache
        self.cost_tracker = cost_tracker

    @classmethod
    def from_config(cls, path: str | Path) -> "LLMManager":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        root = payload.get("llm", payload)
        cache_cfg = root.get("cache", {})
        manager = cls(cache=ResponseCache(ttl=int(cache_cfg.get("ttl", 3600))) if cache_cfg.get("enabled", True) else None, cost_tracker=CostTracker() if root.get("cost_tracking", {}).get("enabled", True) else None)
        for name, raw in root.get("providers", {}).items():
            config = LLMConfig(provider=ModelProvider(raw["provider"]), model=raw["model"], api_key=_expand(raw.get("api_key")), base_url=raw.get("base_url"), temperature=float(raw.get("temperature", 0.7)), max_tokens=int(raw.get("max_tokens", 4096)), top_p=float(raw.get("top_p", 1.0)), priority=int(raw.get("priority", 100)), timeout=float(raw.get("timeout", 120)))
            manager.register_provider(name, config)
        manager.default_provider = root.get("default_provider") or manager.default_provider
        return manager

    def register_provider(self, name: str, config: LLMConfig) -> None:
        provider_class = {ModelProvider.OPENAI: OpenAIProvider, ModelProvider.ANTHROPIC: AnthropicProvider, ModelProvider.OLLAMA: OllamaProvider}.get(config.provider)
        if provider_class is None:
            raise ValueError(f"Unsupported provider: {config.provider}")
        self.providers[name] = provider_class(config)
        self.default_provider = self.default_provider or name

    async def initialize_all(self) -> dict[str, bool]:
        statuses: dict[str, bool] = {}
        for name, provider in self.providers.items():
            try:
                await provider.initialize()
                statuses[name] = True
            except Exception as exc:
                statuses[name] = False
                logger.warning("Provider %s unavailable: %s", name, exc)
        return statuses

    def get_provider(self, name: str | None = None) -> LLMProvider:
        selected = name or self.default_provider
        if not selected or selected not in self.providers:
            raise ValueError(f"Provider '{selected}' is not registered")
        return self.providers[selected]

    def switch_provider(self, name: str) -> LLMProvider:
        provider = self.get_provider(name)
        self.default_provider = name
        return provider

    def get_available_providers(self) -> list[str]:
        return list(self.providers)

    async def chat_with_fallback(self, messages: list[Message], tools: list[ToolDefinition] | None = None, preferred_provider: str | None = None, *, use_cache: bool = True, conversation_id: str | None = None, **kwargs: Any) -> LLMResponse:
        ordered = sorted(self.providers, key=lambda name: (0 if name == (preferred_provider or self.default_provider) else 1, self.providers[name].config.priority, name))
        cache_key = self.cache.make_key(ordered[0] if ordered else "", messages, tools, kwargs) if self.cache and use_cache and ordered else None
        if cache_key and (cached := self.cache.get(cache_key)) is not None:
            return cached
        last_error: Exception | None = None
        for name in ordered:
            provider = self.providers[name]
            try:
                response = await provider.chat(messages, tools, **kwargs)
                if self.cache and cache_key:
                    self.cache.set(cache_key, response)
                if self.cost_tracker:
                    self.cost_tracker.record(provider, response, conversation_id=conversation_id)
                return response
            except Exception as exc:
                last_error = exc
                logger.warning("Provider %s failed; trying fallback: %s", name, exc)
        raise RuntimeError(f"All registered LLM providers failed: {last_error}")


def _expand(value: Any) -> Any:
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        import os
        return os.getenv(value[2:-1])
    return value
