"""Bounded repository worker for Aurora Relay's scheduled dry-run agent loop.

This worker deliberately has no mutation commands. It can inspect a checkout, run
allow-listed validation commands, and write plan/log/report JSON files. Branch
creation and evidence-only commits are handled separately by the workflow.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


SAFE_COMMANDS = [
    (["git", "status", "--short"], Path(".")),
    ([sys.executable, "-m", "compileall", "-q", "backend/app"], Path(".")),
    (["pnpm", "tsc", "--noEmit"], Path("frontend")),
]


def now() -> datetime:
    return datetime.now(UTC)


def run(command: list[str], cwd: Path) -> dict[str, Any]:
    completed = subprocess.run(command, cwd=cwd, check=False, capture_output=True, text=True, timeout=180)
    return {
        "command": " ".join(command),
        "returncode": completed.returncode,
        "stdout": completed.stdout[-4000:],
        "stderr": completed.stderr[-4000:],
        "ok": completed.returncode == 0,
    }


def parse_expiry(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SystemExit("AGENT_LOOP_EXPIRES_AT must be an ISO-8601 UTC timestamp") from exc
    if parsed.tzinfo is None:
        raise SystemExit("AGENT_LOOP_EXPIRES_AT must include a timezone")
    return parsed.astimezone(UTC)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Aurora Relay repository dry-run worker")
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path, default=Path("reports/agent-loop"))
    parser.add_argument("--expires-at", required=True)
    parser.add_argument("--max-actions", type=int, default=8)
    parser.add_argument("--dry-run", action="store_true", required=True)
    args = parser.parse_args()

    if not args.dry_run:
        raise SystemExit("This worker is dry-run only")
    if not 1 <= args.max_actions <= 8:
        raise SystemExit("max-actions must be between 1 and 8")
    expiry = parse_expiry(args.expires_at)
    if now() >= expiry:
        print("Agent-loop window has expired; no actions were executed.")
        return 0

    repository = args.repository.resolve()
    output = (repository / args.output_dir).resolve()
    stamp = now().strftime("%Y%m%dT%H%M%SZ")
    plan = {
        "kind": "aurora-relay-agent-loop-plan",
        "created_at": now().isoformat(),
        "dry_run": True,
        "max_actions": args.max_actions,
        "scope": ["code", "tests", "ui", "connectors"],
        "intended_actions": ["inspect checkout state", "compile backend", "type-check renderer"],
        "blocked_actions": ["merge", "deploy", "release", "delete", "network mutation"],
    }
    write_json(output / f"{stamp}-plan.json", plan)
    actions = [run(command, repository / relative_cwd) for command, relative_cwd in SAFE_COMMANDS[: args.max_actions]]
    succeeded = all(action["ok"] for action in actions)
    report = {
        "kind": "aurora-relay-agent-loop-report",
        "created_at": now().isoformat(),
        "dry_run": True,
        "status": "completed" if succeeded else "failed",
        "actions": actions,
        "reflection": {
            "summary": "No repository source files were changed by the dry-run worker.",
            "recommended_next_step": "Review the evidence-only branch before authorizing any proposed code change.",
        },
        "guardrails": {"max_actions": args.max_actions, "merge": False, "deploy": False, "release": False, "delete": False},
    }
    write_json(output / f"{stamp}-report.json", report)
    print(json.dumps({"status": report["status"], "report": str(output / f"{stamp}-report.json")}, sort_keys=True))
    return 0 if succeeded else 1


if __name__ == "__main__":
    raise SystemExit(main())
