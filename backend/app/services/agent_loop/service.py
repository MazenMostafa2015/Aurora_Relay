from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...config.settings import settings
from ...database.models import AgentLoop, AgentLoopIteration, Connector, User
from .artifacts import AgentLoopArtifactStore


class AgentLoopServiceError(ValueError):
    pass


SAFE_AREAS = {"code", "tests", "docs", "ui", "connectors", "security"}
PROHIBITED_APPROVAL_ACTIONS = {"deploy", "release", "delete", "external"}
DEFAULT_CONFIG: dict[str, Any] = {
    "enabled": False,
    "dry_run": True,
    "schedule": {"frequency": "daily", "times_per_day": 5, "duration_days": 7, "start_time": "08:00", "end_time": "20:00", "time_zone": "UTC"},
    "scope": {"areas": ["code", "tests", "ui", "connectors"], "max_actions_per_loop": 8, "allow_destructive_actions": False},
    "guardrails": {"max_loops_total": 35, "max_consecutive_failures": 3, "require_approval_for": ["deploy", "release", "delete", "external"], "rollback_on_error": True},
    "reporting": {"summary_after_each_loop": True, "daily_digest": True, "final_report": True, "notification_channel": "ui"},
    "repository": {"branch_prefix": "aurora-agent/loop", "allow_review_branch_push": True, "allow_merge": False, "allow_deploy": False, "allow_release": False},
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


class AgentLoopService:
    """Bounded, auditable Think → Act → Reflect orchestration.

    This service intentionally generates dry-run action proposals only. A
    GitHub Actions worker may commit its generated evidence to an isolated
    review branch, but no service method can merge, deploy, release, delete,
    invoke a connector, or execute arbitrary plan text.
    """

    def __init__(self, db: Session, *, artifacts: AgentLoopArtifactStore | None = None) -> None:
        self.db = db
        self.artifacts = artifacts or AgentLoopArtifactStore(
            state_dir=settings.agent_loop_state_dir,
            plan_dir=settings.agent_loop_plan_dir,
            log_dir=settings.agent_loop_log_dir,
            report_dir=settings.agent_loop_report_dir,
        )

    def _validate_config(self, raw: dict[str, Any]) -> dict[str, Any]:
        config = _deep_merge(DEFAULT_CONFIG, raw)
        if config.get("dry_run") is not True:
            raise AgentLoopServiceError("Only dry-run loops are supported; remediation must be reviewed on an isolated branch")
        scope = config["scope"]
        areas = set(scope.get("areas", []))
        if not areas or not areas.issubset(SAFE_AREAS):
            raise AgentLoopServiceError("Loop scope must contain one or more supported safe areas")
        if scope.get("allow_destructive_actions") is not False:
            raise AgentLoopServiceError("Destructive actions are permanently disabled for autonomous loops")
        if int(scope.get("max_actions_per_loop", 0)) < 1 or int(scope["max_actions_per_loop"]) > settings.agent_loop_max_actions:
            raise AgentLoopServiceError(f"max_actions_per_loop must be between 1 and {settings.agent_loop_max_actions}")
        guardrails = config["guardrails"]
        if int(guardrails.get("max_loops_total", 0)) < 1 or int(guardrails["max_loops_total"]) > settings.agent_loop_max_iterations:
            raise AgentLoopServiceError(f"max_loops_total must be between 1 and {settings.agent_loop_max_iterations}")
        if int(guardrails.get("max_consecutive_failures", 0)) < 1 or int(guardrails["max_consecutive_failures"]) > settings.agent_loop_max_consecutive_failures:
            raise AgentLoopServiceError(f"max_consecutive_failures must be between 1 and {settings.agent_loop_max_consecutive_failures}")
        approvals = set(guardrails.get("require_approval_for", []))
        if not PROHIBITED_APPROVAL_ACTIONS.issubset(approvals):
            raise AgentLoopServiceError("deploy, release, delete, and external actions must remain approval-gated")
        schedule = config["schedule"]
        if schedule.get("frequency") != "daily" or int(schedule.get("times_per_day", 0)) != 5 or int(schedule.get("duration_days", 0)) != 7:
            raise AgentLoopServiceError("Repository-backed loops are fixed at five daily runs for seven days")
        repository = config["repository"]
        if repository.get("allow_merge") or repository.get("allow_deploy") or repository.get("allow_release"):
            raise AgentLoopServiceError("Review branches may be pushed, but merge, deployment, and release are disabled")
        return config

    def _get(self, user: User, loop_id: str) -> AgentLoop:
        loop = self.db.scalar(select(AgentLoop).where(AgentLoop.id == loop_id, AgentLoop.user_id == user.id))
        if not loop:
            raise AgentLoopServiceError("Agent loop not found")
        return loop

    def _next_run(self, loop: AgentLoop, now: datetime | None = None) -> datetime | None:
        if not loop.enabled or loop.hard_stop or loop.status in {"paused", "stopped", "completed"}:
            return None
        now = now or _utcnow()
        schedule = loop.config["schedule"]
        start_hour, start_minute = (int(part) for part in schedule["start_time"].split(":"))
        end_hour, end_minute = (int(part) for part in schedule["end_time"].split(":"))
        window_start = now.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
        window_end = now.replace(hour=end_hour, minute=end_minute, second=0, microsecond=0)
        if now >= window_end:
            window_start += timedelta(days=1)
            window_end += timedelta(days=1)
        slots = int(schedule["times_per_day"])
        span_seconds = max(1, (window_end - window_start).total_seconds())
        candidates = [window_start + timedelta(seconds=span_seconds * position / (slots - 1)) for position in range(slots)]
        return next((candidate for candidate in candidates if candidate > now), candidates[-1] + timedelta(days=1))

    def _public(self, loop: AgentLoop) -> dict[str, Any]:
        return {
            "id": loop.id,
            "name": loop.name,
            "enabled": loop.enabled,
            "hard_stop": loop.hard_stop,
            "status": loop.status,
            "config": loop.config,
            "runs_completed": loop.runs_completed,
            "consecutive_failures": loop.consecutive_failures,
            "next_run_at": loop.next_run_at,
            "started_at": loop.started_at,
            "ends_at": loop.ends_at,
            "last_error": loop.last_error,
            "latest_report": loop.latest_report,
            "created_at": loop.created_at,
            "updated_at": loop.updated_at,
        }

    def create_loop(self, user: User, *, name: str, config: dict[str, Any]) -> dict[str, Any]:
        normalized = self._validate_config(config)
        now = _utcnow()
        loop = AgentLoop(user_id=user.id, name=name, config=normalized, enabled=False, status="idle", ends_at=now + timedelta(days=normalized["schedule"]["duration_days"]))
        self.db.add(loop)
        self.db.commit()
        self.db.refresh(loop)
        self._save_snapshot(loop)
        return self._public(loop)

    def list_loops(self, user: User) -> list[dict[str, Any]]:
        loops = self.db.scalars(select(AgentLoop).where(AgentLoop.user_id == user.id).order_by(AgentLoop.updated_at.desc(), AgentLoop.created_at.desc())).all()
        return [self._public(loop) for loop in loops]

    def get_loop(self, user: User, loop_id: str) -> dict[str, Any]:
        return self._public(self._get(user, loop_id))

    def update_loop(self, user: User, loop_id: str, *, name: str | None = None, config: dict[str, Any] | None = None) -> dict[str, Any]:
        loop = self._get(user, loop_id)
        if loop.status == "running":
            raise AgentLoopServiceError("Pause the loop before changing its configuration")
        if name is not None:
            loop.name = name
        if config is not None:
            loop.config = self._validate_config(_deep_merge(loop.config, config))
        self.db.commit()
        self.db.refresh(loop)
        self._save_snapshot(loop)
        return self._public(loop)

    def start(self, user: User, loop_id: str) -> dict[str, Any]:
        loop = self._get(user, loop_id)
        if loop.hard_stop:
            raise AgentLoopServiceError("Hard stop is active; create a new reviewed loop before resuming")
        if loop.runs_completed >= loop.config["guardrails"]["max_loops_total"]:
            raise AgentLoopServiceError("The loop has reached its maximum iteration count")
        now = _utcnow()
        loop.enabled = True
        loop.status = "scheduled"
        loop.started_at = loop.started_at or now
        loop.ends_at = now + timedelta(days=loop.config["schedule"]["duration_days"])
        loop.next_run_at = self._next_run(loop, now)
        self.db.commit()
        self.db.refresh(loop)
        self._save_snapshot(loop)
        return self._public(loop)

    def pause(self, user: User, loop_id: str) -> dict[str, Any]:
        loop = self._get(user, loop_id)
        if loop.status == "running":
            raise AgentLoopServiceError("A running iteration must finish before it can be paused")
        loop.enabled = False
        loop.status = "paused"
        loop.next_run_at = None
        self.db.commit()
        self._save_snapshot(loop)
        return self._public(loop)

    def hard_stop_loop(self, user: User, loop_id: str) -> dict[str, Any]:
        loop = self._get(user, loop_id)
        loop.enabled = False
        loop.hard_stop = True
        loop.status = "stopped"
        loop.next_run_at = None
        loop.last_error = "Stopped manually by operator"
        self.db.commit()
        self._save_snapshot(loop)
        return self._public(loop)

    def _plan_actions(self, loop: AgentLoop) -> list[dict[str, Any]]:
        descriptions = {
            "code": ("inspect_repository_delta", "Review tracked source changes and identify a reviewable improvement opportunity."),
            "tests": ("inspect_validation_health", "Review pre-approved test and build outcomes; propose coverage or regression work."),
            "docs": ("inspect_operator_docs", "Review operator documentation for missing setup, safety, or recovery guidance."),
            "ui": ("inspect_renderer_performance", "Review the production bundle advisory and propose isolated lazy-loading work."),
            "connectors": ("inspect_connector_capabilities", "List redacted configured connector capabilities; do not invoke an external provider."),
            "security": ("inspect_guardrails", "Review configured approval gates, denylisted actions, and audit coverage."),
        }
        limit = loop.config["scope"]["max_actions_per_loop"]
        actions: list[dict[str, Any]] = []
        for index, area in enumerate(loop.config["scope"]["areas"][:limit], start=1):
            action, description = descriptions[area]
            actions.append({"id": f"action-{index}", "area": area, "action": action, "description": description, "state": "proposed", "dry_run": True, "requires_approval": False})
        return actions

    def _redacted_connector_inventory(self, user: User) -> list[dict[str, str]]:
        connectors = self.db.scalars(select(Connector).where(Connector.user_id == user.id, Connector.status == "connected").order_by(Connector.sort_order)).all()
        return [{"provider": connector.provider, "status": connector.status, "display_name": connector.display_name} for connector in connectors]

    @staticmethod
    def _plan_markdown(loop: AgentLoop, iteration: AgentLoopIteration) -> str:
        lines = [f"# Aurora Relay loop {iteration.sequence}", "", "## Think", "", iteration.plan["assessment"], "", "## Proposed dry-run actions", ""]
        lines.extend(f"{index}. **{action['area']}** — {action['description']}" for index, action in enumerate(iteration.actions, start=1))
        lines.extend(["", "## Guardrails", "", "- Dry-run only; no plan text is executed.", "- No deploy, release, delete, merge, or external connector action.", "- Any evidence may be committed only to an isolated `aurora-agent/loop-*` review branch."])
        return "\n".join(lines) + "\n"

    @staticmethod
    def _report_markdown(loop: AgentLoop, iteration: AgentLoopIteration) -> str:
        return "\n".join([
            f"# Aurora Relay loop {iteration.sequence} report",
            "",
            "## Result",
            "",
            "Dry-run plan generated successfully. No source change, external connector call, merge, deployment, release, or deletion was performed.",
            "",
            "## Reflect",
            "",
            iteration.reflection["summary"],
            "",
            "## Next step",
            "",
            "Review the isolated branch evidence, then manually select any proposed remediation for a separately approved task.",
            "",
        ])

    def _save_snapshot(self, loop: AgentLoop) -> None:
        self.artifacts.save_state({"loop": self._public(loop), "saved_at": _utcnow().isoformat()})

    def run_dry_iteration(self, user: User, loop_id: str) -> dict[str, Any]:
        loop = self._get(user, loop_id)
        if loop.hard_stop or loop.status == "stopped":
            raise AgentLoopServiceError("Hard stop is active")
        if loop.runs_completed >= loop.config["guardrails"]["max_loops_total"]:
            loop.enabled = False
            loop.status = "completed"
            self.db.commit()
            self._save_snapshot(loop)
            raise AgentLoopServiceError("The loop has reached its maximum iteration count")
        now = _utcnow()
        loop.status = "running"
        sequence = loop.runs_completed + 1
        actions = self._plan_actions(loop)
        assessment = f"Reviewing loop state after {loop.runs_completed} completed iteration(s), with {len(actions)} bounded dry-run action proposal(s)."
        iteration = AgentLoopIteration(
            loop_id=loop.id,
            user_id=user.id,
            sequence=sequence,
            status="planning",
            dry_run=True,
            branch_name=f"aurora-agent/loop-{sequence}",
            plan={"assessment": assessment, "connectors": self._redacted_connector_inventory(user), "guardrails": deepcopy(loop.config["guardrails"])},
            actions=actions,
            validation={"mode": "dry_run", "executed": False, "reason": "Repository-backed loop is configured to propose, not self-modify."},
        )
        self.db.add(iteration)
        self.db.flush()
        try:
            iteration.plan_path = self.artifacts.write_plan(iteration.id, self._plan_markdown(loop, iteration))
            iteration.log_path = self.artifacts.append_log(iteration.id, {"event": "plan_generated", "loop_id": loop.id, "sequence": sequence, "action_count": len(actions), "dry_run": True})
            iteration.status = "completed"
            iteration.reflection = {"summary": "The bounded dry-run completed without side effects. Proposed work remains pending human review.", "outcome": "review_required"}
            iteration.report_path = self.artifacts.write_report(iteration.id, self._report_markdown(loop, iteration))
            iteration.completed_at = _utcnow()
            loop.runs_completed = sequence
            loop.consecutive_failures = 0
            loop.latest_report = {"iteration_id": iteration.id, "sequence": sequence, "status": iteration.status, "report_path": iteration.report_path, "summary": iteration.reflection["summary"]}
            loop.status = "completed" if sequence >= loop.config["guardrails"]["max_loops_total"] else "scheduled"
            loop.enabled = loop.status == "scheduled"
            loop.next_run_at = self._next_run(loop, now)
            self.db.commit()
            self.db.refresh(iteration)
            self._save_snapshot(loop)
            return self._iteration_public(iteration)
        except Exception as exc:
            iteration.status = "failed"
            iteration.error = str(exc)[:500]
            iteration.completed_at = _utcnow()
            loop.consecutive_failures += 1
            loop.last_error = iteration.error
            if loop.consecutive_failures >= loop.config["guardrails"]["max_consecutive_failures"]:
                loop.status = "stopped"
                loop.hard_stop = True
                loop.enabled = False
                loop.next_run_at = None
            else:
                loop.status = "scheduled"
                loop.next_run_at = self._next_run(loop, now)
            self.db.commit()
            self._save_snapshot(loop)
            raise AgentLoopServiceError("Iteration failed and was recorded without executing any plan action") from exc

    def _iteration_public(self, iteration: AgentLoopIteration) -> dict[str, Any]:
        return {
            "id": iteration.id,
            "loop_id": iteration.loop_id,
            "sequence": iteration.sequence,
            "status": iteration.status,
            "dry_run": iteration.dry_run,
            "branch_name": iteration.branch_name,
            "plan_path": iteration.plan_path,
            "log_path": iteration.log_path,
            "report_path": iteration.report_path,
            "plan": iteration.plan,
            "actions": iteration.actions,
            "reflection": iteration.reflection,
            "validation": iteration.validation,
            "error": iteration.error,
            "started_at": iteration.started_at,
            "completed_at": iteration.completed_at,
        }

    def list_iterations(self, user: User, loop_id: str) -> list[dict[str, Any]]:
        loop = self._get(user, loop_id)
        records = self.db.scalars(select(AgentLoopIteration).where(AgentLoopIteration.loop_id == loop.id, AgentLoopIteration.user_id == user.id).order_by(AgentLoopIteration.sequence.desc())).all()
        return [self._iteration_public(item) for item in records]

    def get_report(self, user: User, loop_id: str, iteration_id: str) -> dict[str, Any]:
        self._get(user, loop_id)
        iteration = self.db.scalar(select(AgentLoopIteration).where(AgentLoopIteration.id == iteration_id, AgentLoopIteration.loop_id == loop_id, AgentLoopIteration.user_id == user.id))
        if not iteration:
            raise AgentLoopServiceError("Agent loop iteration not found")
        return self._iteration_public(iteration)
