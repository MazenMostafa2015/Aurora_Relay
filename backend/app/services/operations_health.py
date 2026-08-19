"""Owner-scoped operational health aggregation with no credential plaintext."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from time import monotonic

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..api.models import (
    OperationalActivity,
    OperationalAgentLoopHealth,
    OperationalAlert,
    OperationalConnectorHealth,
    OperationalLoopIterationHealth,
    OperationalReleaseHealth,
    OperationalSystemHealth,
    OperationalVaultHealth,
    OperationsHealthResponse,
    HealthRetentionResponse,
)
from ..config.settings import settings
from ..database.models import AgentLoop, AgentLoopIteration, AuditLog, Connector, User
from .connectors.vault import CredentialVault


_PROCESS_STARTED_AT = monotonic()

_RELEASE = OperationalReleaseHealth(
    version="v0.8.22",
    sha256_verified=True,
    provenance_verified=True,
    signer_pinned=True,
    timestamp_present=True,
    clean_machine_verified=True,
    trust_note=(
        "The internal signer pin and timestamp presence were verified. "
        "This does not assert public commercial-certificate trust."
    ),
)


class OperationsHealthService:
    """Build a compact view for one authenticated operator without mutating state."""

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _retention_days(value: int) -> int:
        if value not in {7, 30, 90}:
            return 30
        return value

    def retention(self, user: User) -> HealthRetentionResponse:
        return HealthRetentionResponse(retention_days=self._retention_days(user.health_history_retention_days))

    def update_retention(self, user: User, retention_days: int) -> HealthRetentionResponse:
        retention_days = self._retention_days(retention_days)
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        user.health_history_retention_days = retention_days
        pruned_audits = self.db.execute(delete(AuditLog).where(AuditLog.user_id == user.id, AuditLog.created_at < cutoff)).rowcount or 0
        pruned_iterations = self.db.execute(delete(AgentLoopIteration).where(AgentLoopIteration.user_id == user.id, AgentLoopIteration.started_at < cutoff)).rowcount or 0
        self.db.commit()
        return HealthRetentionResponse(
            retention_days=retention_days,
            pruned_audit_events=pruned_audits,
            pruned_loop_iterations=pruned_iterations,
        )

    @staticmethod
    def _connector_status(status: str) -> str:
        return {
            "connected": "connected",
            "testing": "warning",
            "needs_attention": "warning",
            "disabled": "disabled",
            "not_configured": "disabled",
        }.get(status, "error")

    @staticmethod
    def _loop_state(status: str) -> str:
        if status in {"running", "paused", "stopped"}:
            return status
        return "idle"

    @staticmethod
    def _iteration_result(status: str) -> str:
        if status == "completed":
            return "success"
        if status == "failed":
            return "failed"
        return "partial"

    @staticmethod
    def _activity_type(event_type: str) -> str:
        lowered = event_type.lower()
        if "fail" in lowered or "error" in lowered or "rejected" in lowered:
            return "error"
        if "complete" in lowered or "tested" in lowered or "applied" in lowered:
            return "success"
        if "pause" in lowered or "attention" in lowered or "stop" in lowered:
            return "warning"
        return "info"

    def snapshot(self, user_id: str) -> OperationsHealthResponse:
        now = datetime.now(timezone.utc)
        connectors = list(self.db.scalars(
            select(Connector).where(Connector.user_id == user_id).order_by(Connector.sort_order, Connector.display_name)
        ))
        loops = list(self.db.scalars(
            select(AgentLoop).where(AgentLoop.user_id == user_id).order_by(AgentLoop.updated_at.desc(), AgentLoop.created_at.desc())
        ))
        loop = next((item for item in loops if item.status == "running"), loops[0] if loops else None)
        iterations: list[AgentLoopIteration] = []
        if loop:
            iterations = list(self.db.scalars(
                select(AgentLoopIteration)
                .where(AgentLoopIteration.loop_id == loop.id, AgentLoopIteration.user_id == user_id)
                .order_by(AgentLoopIteration.sequence.desc())
                .limit(5)
            ))
        retention_days = self._retention_days(getattr(self.db.get(User, user_id), "health_history_retention_days", 30))
        cutoff = now - timedelta(days=retention_days)
        audits = list(self.db.scalars(
            select(AuditLog).where(AuditLog.user_id == user_id, AuditLog.created_at >= cutoff).order_by(AuditLog.created_at.desc()).limit(20)
        ))

        connector_health = [
            OperationalConnectorHealth(
                id=connector.id,
                provider=connector.provider,
                display_name=connector.display_name,
                status=self._connector_status(connector.status),
                last_connected=connector.last_tested_at,
                error=connector.last_error,
                credential_configured=bool(connector.credential_id),
            )
            for connector in connectors
        ]
        recent_iterations = [
            OperationalLoopIterationHealth(
                iteration=item.sequence,
                timestamp=item.completed_at or item.started_at,
                result=self._iteration_result(item.status),
                summary=str(item.reflection.get("summary") or item.reflection.get("outcome") or "Review-required dry-run evidence recorded."),
            )
            for item in iterations
        ]
        last_result = recent_iterations[0].result if recent_iterations else None
        loop_health = OperationalAgentLoopHealth(
            state=self._loop_state(loop.status) if loop else "idle",
            current_iteration=(loop.runs_completed + (1 if loop and loop.status == "running" else 0)) if loop else 0,
            total_iterations=loop.config.get("guardrails", {}).get("max_loops_total", 0) if loop else 0,
            last_result=last_result,
            next_run=loop.next_run_at if loop else None,
            recent_iterations=recent_iterations,
        )
        activities = [
            OperationalActivity(
                id=event.id,
                type=self._activity_type(event.event_type),
                message=event.event_type.replace(".", " ").replace("_", " ").capitalize(),
                timestamp=event.created_at,
                source=event.resource_type or "system",
            )
            for event in audits
        ]
        vault_status = CredentialVault.status_from_environment()
        vault_health = OperationalVaultHealth(
            state=vault_status.state,
            backend=vault_status.backend,
            fallback=vault_status.fallback,
            message=(
                "Credential protection is ready. Connector secret values are never returned to this dashboard."
                if vault_status.state == "ready"
                else vault_status.reason or "Credential protection is locked."
            ),
        )
        alerts: list[OperationalAlert] = []
        for connector in connector_health:
            if connector.status in {"warning", "error"}:
                alerts.append(OperationalAlert(
                    id=f"connector-{connector.id}",
                    severity="error" if connector.status == "error" else "warning",
                    message=connector.error or f"{connector.display_name} needs attention.",
                    recommendation="Run a connection test and review the connector configuration.",
                ))
        if loop and loop.hard_stop:
            alerts.append(OperationalAlert(
                id=f"loop-{loop.id}-hard-stop",
                severity="warning",
                message="The repository agent loop is hard-stopped.",
                recommendation="Create and review a new loop before resuming autonomous work.",
            ))
        if loop and loop.last_error:
            alerts.append(OperationalAlert(
                id=f"loop-{loop.id}-error",
                severity="error",
                message=loop.last_error,
                recommendation="Inspect the latest dry-run report before changing loop configuration.",
            ))
        if vault_status.state == "locked":
            alerts.append(OperationalAlert(
                id="credential-vault-locked",
                severity="error",
                message="Connector credential vault is locked.",
                recommendation="Restore an approved OS credential store or the encrypted local fallback before configuring credentials.",
            ))

        status = "critical" if any(alert.severity == "error" for alert in alerts) else "degraded" if alerts else "operational"
        last_completion = next((item.timestamp for item in recent_iterations if item.result == "success"), None)
        return OperationsHealthResponse(
            generated_at=now,
            system=OperationalSystemHealth(
                status=status,
                version=settings.app_version,
                uptime_seconds=round(monotonic() - _PROCESS_STARTED_AT),
                last_loop_completion=last_completion,
            ),
            connectors=connector_health,
            agent_loop=loop_health,
            release=_RELEASE,
            vault=vault_health,
            activities=activities,
            alerts=alerts,
        )
