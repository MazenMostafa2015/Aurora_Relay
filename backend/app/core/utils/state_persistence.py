"""Durable JSON persistence for resumable task state."""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from ..models.task import Task


class StatePersistence:
    def __init__(self, storage_dir: str | Path = "data/tasks") -> None:
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def save_task(self, task: Task) -> Path:
        target = self.storage_dir / f"{task.id}.json"
        fd, temporary = tempfile.mkstemp(dir=self.storage_dir, prefix=f".{task.id}.", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(task.to_dict(), handle, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return target

    def load_task(self, task_id: str) -> Task | None:
        path = self.storage_dir / f"{task_id}.json"
        if not path.exists():
            return None
        return Task.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def load_task_dict(self, task_id: str) -> dict[str, Any] | None:
        path = self.storage_dir / f"{task_id}.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    def list_tasks(self) -> list[str]:
        return sorted(path.stem for path in self.storage_dir.glob("*.json"))

    def delete_task(self, task_id: str) -> bool:
        path = self.storage_dir / f"{task_id}.json"
        if not path.exists():
            return False
        path.unlink()
        return True

    def cleanup_old_tasks(self, days: int = 30) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        deleted = 0
        for path in self.storage_dir.glob("*.json"):
            try:
                created = datetime.fromisoformat(json.loads(path.read_text(encoding="utf-8"))["created_at"])
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
                if created < cutoff:
                    path.unlink()
                    deleted += 1
            except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
                continue
        return deleted
