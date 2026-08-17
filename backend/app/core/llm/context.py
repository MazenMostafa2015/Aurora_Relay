"""Conversation state and bounded context-window management."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .provider import Message


def estimate_tokens(text: str | None) -> int:
    return max(0, len(text or "") // 4)


@dataclass(slots=True)
class ConversationContext:
    conversation_id: str
    messages: list[Message] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    max_tokens: int = 128000
    token_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def add_message(self, message: Message) -> None:
        self.messages.append(message)
        self.token_count += estimate_tokens(message.content)
        self.updated_at = datetime.now(timezone.utc).isoformat()
        self.truncate_if_needed()

    def get_messages(self, limit: int | None = None) -> list[Message]:
        return self.messages[-limit:] if limit and len(self.messages) > limit else list(self.messages)

    def truncate_if_needed(self, max_tokens: int | None = None) -> None:
        target = max_tokens or self.max_tokens
        if self.token_count <= target:
            return
        system = [message for message in self.messages if message.role == "system"]
        others = [message for message in self.messages if message.role != "system"]
        self.messages = system + others
        while others and sum(estimate_tokens(item.content) for item in self.messages) > target:
            others.pop(0)
            self.messages = system + others
        self.token_count = sum(estimate_tokens(item.content) for item in self.messages)
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {"conversation_id": self.conversation_id, "messages": [message.to_dict() for message in self.messages], "metadata": self.metadata, "max_tokens": self.max_tokens, "token_count": self.token_count, "created_at": self.created_at, "updated_at": self.updated_at}


class ContextManager:
    def __init__(self, max_tokens: int = 128000) -> None:
        self.max_tokens = max_tokens
        self.contexts: dict[str, ConversationContext] = {}

    def get_or_create_context(self, conversation_id: str) -> ConversationContext:
        if conversation_id not in self.contexts:
            self.contexts[conversation_id] = ConversationContext(conversation_id, max_tokens=self.max_tokens)
        return self.contexts[conversation_id]

    def add_message(self, conversation_id: str, message: Message) -> None:
        self.get_or_create_context(conversation_id).add_message(message)

    def get_context_messages(self, conversation_id: str, limit: int | None = None) -> list[Message]:
        return self.get_or_create_context(conversation_id).get_messages(limit)

    def clear(self, conversation_id: str) -> None:
        self.contexts.pop(conversation_id, None)
