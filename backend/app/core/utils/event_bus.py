"""Async event bus used for real-time orchestrator updates."""
from __future__ import annotations

import asyncio
import inspect
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

EventCallback = Callable[[str, dict[str, Any]], Any]


class EventBus:
    def __init__(self, max_history: int = 1000) -> None:
        self._subscribers: dict[str, list[EventCallback]] = defaultdict(list)
        self._history: list[dict[str, Any]] = []
        self.max_history = max_history

    def subscribe(self, event_type: str, callback: EventCallback) -> None:
        if callback not in self._subscribers[event_type]:
            self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: EventCallback) -> None:
        if callback in self._subscribers.get(event_type, []):
            self._subscribers[event_type].remove(callback)

    async def emit(self, event_type: str, data: dict[str, Any]) -> dict[str, Any]:
        event = {"type": event_type, "data": data, "timestamp": datetime.now(timezone.utc).isoformat()}
        self._history.append(event)
        self._history = self._history[-self.max_history:]
        callbacks = list(self._subscribers.get(event_type, [])) + list(self._subscribers.get("*", []))
        await asyncio.gather(*(self._invoke(callback, event_type, data) for callback in callbacks), return_exceptions=True)
        return event

    async def _invoke(self, callback: EventCallback, event_type: str, data: dict[str, Any]) -> None:
        result = callback(event_type, data)
        if inspect.isawaitable(result):
            await result

    def get_history(self, event_type: str | None = None, task_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        events = self._history
        if event_type:
            events = [event for event in events if event["type"] == event_type]
        if task_id:
            events = [event for event in events if event["data"].get("task_id") == task_id]
        return events[-limit:]

    def clear_history(self) -> None:
        self._history.clear()


event_bus = EventBus()
