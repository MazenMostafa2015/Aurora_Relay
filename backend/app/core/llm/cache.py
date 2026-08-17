"""Small local response cache with deterministic keys and TTL expiry."""
from __future__ import annotations

import hashlib
import json
import threading
import time
from typing import Any

from .provider import LLMResponse, Message, ToolDefinition


class ResponseCache:
    def __init__(self, ttl: int = 3600, max_entries: int = 1000) -> None:
        self.ttl = ttl
        self.max_entries = max_entries
        self._entries: dict[str, tuple[float, LLMResponse]] = {}
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    @staticmethod
    def make_key(provider: str, messages: list[Message], tools: list[ToolDefinition] | None, kwargs: dict[str, Any]) -> str:
        payload = {"provider": provider, "messages": [message.to_dict() for message in messages], "tools": [tool.to_openai() for tool in tools] if tools else [], "kwargs": kwargs}
        return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()

    def get(self, key: str) -> LLMResponse | None:
        with self._lock:
            entry = self._entries.get(key)
            if not entry:
                self.misses += 1
                return None
            expires, response = entry
            if expires <= time.time():
                self._entries.pop(key, None)
                self.misses += 1
                return None
            self.hits += 1
            return response

    def set(self, key: str, response: LLMResponse) -> None:
        with self._lock:
            if len(self._entries) >= self.max_entries:
                oldest = min(self._entries, key=lambda item: self._entries[item][0])
                self._entries.pop(oldest, None)
            self._entries[key] = (time.time() + self.ttl, response)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def stats(self) -> dict[str, int]:
        return {"entries": len(self._entries), "hits": self.hits, "misses": self.misses}
