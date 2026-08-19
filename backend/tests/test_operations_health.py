from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

from backend.app.database.models import (
    AgentLoop,
    AgentLoopIteration,
    AuditLog,
    Base,
    Connector,
    ConnectorCredential,
    User,
)
from backend.app.services.operations_health import OperationsHealthService


def _session() -> Session:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_health_snapshot_is_owner_scoped_and_excludes_vault_ciphertext() -> None:
    db = _session()
    owner = User(username="health-owner", email="health-owner@example.test", password_hash="not-a-real-password")
    other = User(username="health-other", email="health-other@example.test", password_hash="not-a-real-password")
    db.add_all([owner, other])
    db.commit()
    db.refresh(owner)
    db.refresh(other)

    credential = ConnectorCredential(
        user_id=owner.id,
        provider="github",
        label="Owner token",
        ciphertext="encrypted-secret-that-must-never-reach-health",
    )
    db.add(credential)
    db.commit()
    db.refresh(credential)

    owner_connector = Connector(
        user_id=owner.id,
        provider="github",
        display_name="Owner GitHub",
        status="needs_attention",
        credential_id=credential.id,
        last_error="Connection requires review",
    )
    other_connector = Connector(
        user_id=other.id,
        provider="revit",
        display_name="Other Revit",
        status="connected",
    )
    loop = AgentLoop(
        user_id=owner.id,
        name="Owner review loop",
        hard_stop=True,
        status="stopped",
        runs_completed=2,
        config={"guardrails": {"max_loops_total": 35}},
    )
    db.add_all([owner_connector, other_connector, loop])
    db.commit()
    db.refresh(loop)
    db.add_all([
        AgentLoopIteration(
            loop_id=loop.id,
            user_id=owner.id,
            sequence=2,
            status="completed",
            dry_run=True,
            reflection={"outcome": "review_required"},
            completed_at=datetime.now(timezone.utc),
        ),
        AuditLog(
            user_id=owner.id,
            event_type="connector.tested",
            resource_type="connector",
            resource_id=owner_connector.id,
            details={"safe": True},
        ),
        AuditLog(
            user_id=other.id,
            event_type="connector.failed",
            resource_type="connector",
            resource_id=other_connector.id,
            details={"safe": True},
        ),
    ])
    db.commit()

    snapshot = OperationsHealthService(db).snapshot(owner.id)
    payload = snapshot.model_dump_json()

    assert [connector.display_name for connector in snapshot.connectors] == ["Owner GitHub"]
    assert snapshot.connectors[0].credential_configured is True
    assert snapshot.agent_loop.state == "stopped"
    assert snapshot.agent_loop.total_iterations == 35
    assert snapshot.agent_loop.recent_iterations[0].summary == "review_required"
    assert snapshot.release.version == "v0.8.22"
    assert snapshot.release.sha256_verified is True
    assert "connection requires review" in " ".join(alert.message.lower() for alert in snapshot.alerts)
    assert any("hard-stopped" in alert.message for alert in snapshot.alerts)
    assert [activity.message for activity in snapshot.activities] == ["Connector tested"]
    assert "encrypted-secret-that-must-never-reach-health" not in payload
    assert "Other Revit" not in payload
    db.close()


def test_health_snapshot_without_local_records_is_operational_and_empty() -> None:
    db = _session()
    owner = User(username="empty-health", email="empty-health@example.test", password_hash="not-a-real-password")
    db.add(owner)
    db.commit()
    db.refresh(owner)

    snapshot = OperationsHealthService(db).snapshot(owner.id)

    assert snapshot.system.status == "operational"
    assert snapshot.connectors == []
    assert snapshot.agent_loop.state == "idle"
    assert snapshot.alerts == []
    assert snapshot.activities == []
    db.close()


def test_health_snapshot_reports_locked_vault_without_secret_material(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AURORA_CONNECTOR_VAULT_LOCKED", "1")
    monkeypatch.setenv("AURORA_CONNECTOR_VAULT_BACKEND", "windows-credential-vault")
    db = _session()
    owner = User(username="locked-health", email="locked-health@example.test", password_hash="not-a-real-password")
    db.add(owner)
    db.commit()
    db.refresh(owner)

    snapshot = OperationsHealthService(db).snapshot(owner.id)
    payload = snapshot.model_dump_json()

    assert snapshot.vault.state == "locked"
    assert snapshot.vault.backend == "windows-credential-vault"
    assert any(alert.id == "credential-vault-locked" for alert in snapshot.alerts)
    assert "AURORA_CONNECTOR_VAULT_KEY" not in payload
    db.close()


def test_health_retention_prunes_only_expired_owner_history() -> None:
    db = _session()
    owner = User(username="retention-owner", email="retention-owner@example.test", password_hash="not-a-real-password")
    other = User(username="retention-other", email="retention-other@example.test", password_hash="not-a-real-password")
    db.add_all([owner, other])
    db.commit()
    db.refresh(owner)
    db.refresh(other)
    loop = AgentLoop(user_id=owner.id, name="retention loop", config={})
    db.add(loop)
    db.commit()
    db.refresh(loop)
    stale = datetime.now(timezone.utc) - timedelta(days=8)
    db.add_all([
        AuditLog(user_id=owner.id, event_type="old.owner", created_at=stale),
        AuditLog(user_id=other.id, event_type="old.other", created_at=stale),
        AuditLog(user_id=owner.id, event_type="fresh.owner", created_at=datetime.now(timezone.utc)),
        AgentLoopIteration(loop_id=loop.id, user_id=owner.id, sequence=1, status="completed", dry_run=True, started_at=stale),
    ])
    db.commit()

    result = OperationsHealthService(db).update_retention(owner, 7)

    assert result.retention_days == 7
    assert result.pruned_audit_events == 1
    assert result.pruned_loop_iterations == 1
    assert OperationsHealthService(db).retention(owner).retention_days == 7
    assert db.query(AuditLog).filter(AuditLog.user_id == other.id).count() == 1
    assert db.query(AuditLog).filter(AuditLog.user_id == owner.id).count() == 1
    db.close()
