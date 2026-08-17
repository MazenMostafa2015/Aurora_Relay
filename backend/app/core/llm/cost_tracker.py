"""Usage and cost accounting for remote and local LLM calls."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from .provider import LLMProvider, LLMResponse


@dataclass(slots=True)
class CostEntry:
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost: float
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    conversation_id: str | None = None


class CostTracker:
    """Tracks token usage; Ollama defaults to zero cost."""

    PRICING_PER_1K: dict[tuple[str, str], tuple[float, float]] = {
        ("openai", "gpt-4-turbo"): (0.01, 0.03),
        ("openai", "gpt-4o"): (0.005, 0.015),
        ("openai", "gpt-3.5-turbo"): (0.0005, 0.0015),
        ("anthropic", "claude-3-haiku-20240307"): (0.00025, 0.00125),
        ("anthropic", "claude-3-5-sonnet-20241022"): (0.003, 0.015),
    }

    def __init__(self, pricing: dict[tuple[str, str], tuple[float, float]] | None = None) -> None:
        self.pricing = pricing or dict(self.PRICING_PER_1K)
        self.entries: list[CostEntry] = []

    def calculate_cost(self, provider: str, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        if provider == "ollama":
            return 0.0
        prompt_rate, completion_rate = self.pricing.get((provider, model), (0.0, 0.0))
        return prompt_tokens / 1000 * prompt_rate + completion_tokens / 1000 * completion_rate

    def record(self, provider: LLMProvider, response: LLMResponse, conversation_id: str | None = None) -> CostEntry:
        usage = response.usage or {}
        prompt = int(usage.get("prompt_tokens", 0))
        completion = int(usage.get("completion_tokens", 0))
        model = response.model or provider.get_model_name()
        entry = CostEntry(provider.provider_name, model, prompt, completion, prompt + completion, self.calculate_cost(provider.provider_name, model, prompt, completion), conversation_id=conversation_id)
        self.entries.append(entry)
        return entry

    def summary(self) -> dict[str, Any]:
        return {"total_cost": sum(entry.cost for entry in self.entries), "total_calls": len(self.entries), "total_tokens": sum(entry.total_tokens for entry in self.entries), "by_provider": self._group(lambda e: e.provider), "by_model": self._group(lambda e: f"{e.provider}/{e.model}")}

    def _group(self, key_fn):
        grouped: dict[str, dict[str, float | int]] = {}
        for entry in self.entries:
            key = key_fn(entry)
            item = grouped.setdefault(key, {"cost": 0.0, "calls": 0, "tokens": 0})
            item["cost"] += entry.cost
            item["calls"] += 1
            item["tokens"] += entry.total_tokens
        return grouped

    def export_json(self) -> str:
        return json.dumps({"entries": [asdict(entry) for entry in self.entries], "summary": self.summary()}, indent=2)

    def reset(self) -> None:
        self.entries.clear()
