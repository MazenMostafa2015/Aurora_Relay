from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AgentLoopArtifactStore:
    """Constrained local output writer for plans, logs, reports, and state.

    The paths are operator-controlled settings, while generated filenames are
    derived exclusively from UUID-like iteration identifiers. This prevents an
    agent plan from selecting an arbitrary filesystem destination.
    """

    def __init__(self, *, state_dir: str, plan_dir: str, log_dir: str, report_dir: str) -> None:
        self.state_dir = Path(state_dir).expanduser().resolve()
        self.plan_dir = Path(plan_dir).expanduser().resolve()
        self.log_dir = Path(log_dir).expanduser().resolve()
        self.report_dir = Path(report_dir).expanduser().resolve()
        for directory in (self.state_dir, self.plan_dir, self.log_dir, self.report_dir):
            directory.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _atomic_write(path: Path, content: str) -> None:
        temporary = path.with_suffix(f"{path.suffix}.tmp")
        temporary.write_text(content, encoding="utf-8")
        os.replace(temporary, path)

    def save_state(self, state: dict[str, Any]) -> str:
        path = self.state_dir / "agent-loop.json"
        self._atomic_write(path, json.dumps(state, indent=2, sort_keys=True, default=str))
        return str(path)

    def write_plan(self, iteration_id: str, content: str) -> str:
        path = self.plan_dir / f"loop-{iteration_id}.md"
        self._atomic_write(path, content)
        return str(path)

    def append_log(self, iteration_id: str, event: dict[str, Any]) -> str:
        path = self.log_dir / f"loop-{iteration_id}.jsonl"
        line = json.dumps({"timestamp": datetime.now(timezone.utc).isoformat(), **event}, sort_keys=True, default=str) + "\n"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line)
        return str(path)

    def write_report(self, iteration_id: str, content: str) -> str:
        path = self.report_dir / f"loop-{iteration_id}.md"
        self._atomic_write(path, content)
        return str(path)
