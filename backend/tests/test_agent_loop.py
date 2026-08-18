from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database.models import Base, User
from backend.app.services.agent_loop.artifacts import AgentLoopArtifactStore
from backend.app.services.agent_loop.service import AgentLoopService, AgentLoopServiceError


@pytest.fixture()
def db() -> Session:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


def user(db: Session, username: str = "operator") -> User:
    account = User(username=username, email=f"{username}@example.test", password_hash="not-a-real-password")
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def service(db: Session, root: Path) -> AgentLoopService:
    return AgentLoopService(
        db,
        artifacts=AgentLoopArtifactStore(
            state_dir=str(root / "state"),
            plan_dir=str(root / "plans"),
            log_dir=str(root / "logs"),
            report_dir=str(root / "reports"),
        ),
    )


def test_dry_iteration_writes_reviewable_evidence_without_side_effects(db: Session, tmp_path: Path) -> None:
    account = user(db)
    loops = service(db, tmp_path)
    loop = loops.create_loop(account, name="Safe repository review", config={})
    started = loops.start(account, loop["id"])

    iteration = loops.run_dry_iteration(account, loop["id"])

    assert started["status"] == "scheduled"
    assert iteration["status"] == "completed"
    assert iteration["dry_run"] is True
    assert iteration["branch_name"] == "aurora-agent/loop-1"
    assert iteration["validation"]["executed"] is False
    assert Path(iteration["plan_path"]).is_file()
    assert Path(iteration["log_path"]).is_file()
    assert Path(iteration["report_path"]).is_file()
    assert "No source change" in Path(iteration["report_path"]).read_text(encoding="utf-8")


def test_loop_rejects_non_dry_run_and_relaxed_approval_guards(db: Session, tmp_path: Path) -> None:
    account = user(db)
    loops = service(db, tmp_path)

    with pytest.raises(AgentLoopServiceError, match="Only dry-run"):
        loops.create_loop(account, name="Unsafe", config={"dry_run": False})
    with pytest.raises(AgentLoopServiceError, match="approval-gated"):
        loops.create_loop(account, name="Unsafe", config={"guardrails": {"require_approval_for": ["deploy"]}})
    with pytest.raises(AgentLoopServiceError, match="merge"):
        loops.create_loop(account, name="Unsafe", config={"repository": {"allow_merge": True}})


def test_loop_owner_scope_and_hard_stop_prevent_future_iterations(db: Session, tmp_path: Path) -> None:
    account = user(db)
    other = user(db, "other")
    loops = service(db, tmp_path)
    loop = loops.create_loop(account, name="Scoped", config={})

    with pytest.raises(AgentLoopServiceError, match="not found"):
        loops.get_loop(other, loop["id"])

    stopped = loops.hard_stop_loop(account, loop["id"])
    assert stopped["hard_stop"] is True
    assert stopped["status"] == "stopped"
    with pytest.raises(AgentLoopServiceError, match="Hard stop"):
        loops.run_dry_iteration(account, loop["id"])


def test_three_consecutive_internal_failures_force_hard_stop(db: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    account = user(db)
    loops = service(db, tmp_path)
    loop = loops.create_loop(account, name="Failure safety", config={})

    def fail(*_args, **_kwargs):
        raise OSError("storage unavailable")

    monkeypatch.setattr(loops.artifacts, "write_plan", fail)
    for _ in range(3):
        with pytest.raises(AgentLoopServiceError, match="Iteration failed"):
            loops.run_dry_iteration(account, loop["id"])

    state = loops.get_loop(account, loop["id"])
    assert state["consecutive_failures"] == 3
    assert state["hard_stop"] is True
    assert state["enabled"] is False
    assert state["status"] == "stopped"
