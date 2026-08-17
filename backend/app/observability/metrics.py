from __future__ import annotations

import json
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from threading import Lock
from typing import Any


@dataclass
class RequestMetric:
    count: int = 0
    total_seconds: float = 0.0


class MetricsRegistry:
    """Small dependency-free metrics registry with Prometheus text output."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._requests: dict[tuple[str, str, str], RequestMetric] = defaultdict(RequestMetric)
        self._errors: Counter[str] = Counter()
        self._tasks_created = 0

    def observe_request(self, method: str, path: str, status: int, duration: float) -> None:
        with self._lock:
            metric = self._requests[(method, path, str(status))]
            metric.count += 1
            metric.total_seconds += duration
            if status >= 500:
                self._errors[path] += 1

    def increment_tasks(self) -> None:
        with self._lock:
            self._tasks_created += 1

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "requests": {"|".join(key): {"count": value.count, "total_seconds": value.total_seconds} for key, value in self._requests.items()},
                "errors": dict(self._errors),
                "tasks_created": self._tasks_created,
            }

    def prometheus(self) -> str:
        lines = [
            "# HELP manus_http_requests_total Total HTTP requests by method, path, and status.",
            "# TYPE manus_http_requests_total counter",
        ]
        with self._lock:
            for (method, path, status), metric in self._requests.items():
                labels = f'method="{method}",path="{path}",status="{status}"'
                lines.append(f"manus_http_requests_total{{{labels}}} {metric.count}")
            lines.extend([
                "# HELP manus_tasks_created_total Tasks accepted by the API.",
                "# TYPE manus_tasks_created_total counter",
                f"manus_tasks_created_total {self._tasks_created}",
                "# HELP manus_http_request_seconds_total Total observed request duration.",
                "# TYPE manus_http_request_seconds_total counter",
            ])
            for (method, path, status), metric in self._requests.items():
                labels = f'method="{method}",path="{path}",status="{status}"'
                lines.append(f"manus_http_request_seconds_total{{{labels}}} {metric.total_seconds:.6f}")
        return "\n".join(lines) + "\n"


metrics = MetricsRegistry()


def log_event(event: str, **fields: Any) -> None:
    print(json.dumps({"ts": time.time(), "event": event, **fields}, sort_keys=True), flush=True)
