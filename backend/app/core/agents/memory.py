"""In-process memory manager for agent context and learned facts."""
from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class MemoryEntry:
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    importance: float = 0.5
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    access_count: int = 0
    last_accessed: datetime | None = None

    @property
    def id(self) -> str:
        return hashlib.sha256(f"{self.content}|{sorted(self.metadata.items())}|{self.timestamp.isoformat()}".encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "content": self.content, "metadata": self.metadata, "importance": self.importance, "timestamp": self.timestamp.isoformat(), "access_count": self.access_count, "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None}


class MemoryManager:
    def __init__(self, max_short_term: int = 50, max_long_term: int = 1000) -> None:
        self.short_term: list[MemoryEntry] = []
        self.long_term: dict[str, MemoryEntry] = {}
        self.task_memory: dict[str, list[MemoryEntry]] = defaultdict(list)
        self.max_short_term = max_short_term
        self.max_long_term = max_long_term

    def add_short_term(self, content: str, metadata: dict[str, Any] | None = None, importance: float = 0.5) -> MemoryEntry:
        entry = MemoryEntry(content, metadata or {}, importance)
        self.short_term.append(entry)
        if len(self.short_term) > self.max_short_term:
            self.short_term.sort(key=lambda item: (item.importance, item.timestamp))
            self.short_term = self.short_term[-self.max_short_term:]
        return entry

    def add_long_term(self, content: str, metadata: dict[str, Any] | None = None, importance: float = 0.5) -> MemoryEntry:
        entry = MemoryEntry(content, metadata or {}, importance)
        self.long_term[entry.id] = entry
        if len(self.long_term) > self.max_long_term:
            ordered = sorted(self.long_term.values(), key=lambda item: (item.importance * (1 + item.access_count), item.timestamp))
            for stale in ordered[: len(self.long_term) - self.max_long_term]:
                self.long_term.pop(stale.id, None)
        return entry

    def add_task_memory(self, task_id: str, content: str, metadata: dict[str, Any] | None = None, importance: float = 0.5) -> MemoryEntry:
        entry = MemoryEntry(content, metadata or {}, importance)
        self.task_memory[task_id].append(entry)
        return entry

    def _score(self, entry: MemoryEntry, query: str) -> float:
        query_l = query.lower()
        score = (2.0 if query_l in entry.content.lower() else 0.0) + sum(0.5 for value in entry.metadata.values() if query_l in str(value).lower())
        return score * max(entry.importance, 0.01)

    def get_short_term(self, query: str | None = None, limit: int = 10) -> list[MemoryEntry]:
        if not query:
            return self.short_term[-limit:]
        return sorted(self.short_term, key=lambda item: self._score(item, query), reverse=True)[:limit]

    def get_long_term(self, query: str, limit: int = 5) -> list[MemoryEntry]:
        results = sorted(self.long_term.values(), key=lambda item: self._score(item, query), reverse=True)[:limit]
        for item in results:
            item.access_count += 1
            item.last_accessed = datetime.now(timezone.utc)
        return results

    def get_task_memory(self, task_id: str, limit: int = 20) -> list[MemoryEntry]:
        return self.task_memory.get(task_id, [])[-limit:]

    def consolidate_memories(self, threshold: float = 0.7) -> int:
        promoted = [entry for entry in self.short_term if entry.importance >= threshold]
        for entry in promoted:
            self.long_term[entry.id] = entry
            self.short_term.remove(entry)
        return len(promoted)

    def context_summary(self, query: str | None = None) -> str:
        recent = self.get_short_term(query, 5)
        relevant = self.get_long_term(query, 3) if query else list(self.long_term.values())[-3:]
        return "Recent context:\n" + "\n".join(f"- {item.content[:200]}" for item in recent) + "\nRelevant long-term knowledge:\n" + "\n".join(f"- {item.content[:200]}" for item in relevant)
