"""Provider-neutral LLM contracts and normalized response models."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator


class ModelProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"


@dataclass(slots=True)
class LLMConfig:
    provider: ModelProvider
    model: str
    api_key: str | None = None
    base_url: str | None = None
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    timeout: float = 120.0
    priority: int = 100
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Message:
    role: str
    content: str | None = None
    name: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"role": self.role, "content": self.content}
        if self.name:
            result["name"] = self.name
        if self.tool_calls:
            result["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            result["tool_call_id"] = self.tool_call_id
        return result


@dataclass(slots=True)
class ToolDefinition:
    name: str
    description: str
    parameters: dict[str, Any]

    def to_openai(self) -> dict[str, Any]:
        return {"type": "function", "function": {"name": self.name, "description": self.description, "parameters": self.parameters}}


@dataclass(slots=True)
class LLMResponse:
    content: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    finish_reason: str | None = None
    usage: dict[str, int] | None = None
    model: str | None = None
    provider: str | None = None
    raw: Any = None


class LLMProvider(ABC):
    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        self._initialized = False

    @abstractmethod
    async def initialize(self) -> None:
        """Validate credentials and establish the provider client."""

    @abstractmethod
    async def chat(self, messages: list[Message], tools: list[ToolDefinition] | None = None, stream: bool = False, **kwargs: Any) -> LLMResponse:
        """Return one normalized model response."""

    @abstractmethod
    async def stream_chat(self, messages: list[Message], tools: list[ToolDefinition] | None = None, **kwargs: Any) -> AsyncIterator[str]:
        """Yield text deltas as they arrive from the provider."""
        if False:
            yield ""

    async def extract_tool_calls(self, response: LLMResponse) -> list[dict[str, Any]]:
        return response.tool_calls or []

    def get_model_name(self) -> str:
        return self.config.model

    @property
    def provider_name(self) -> str:
        return self.config.provider.value
