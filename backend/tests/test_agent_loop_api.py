from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.api.dependencies import get_current_user
from backend.app.api.routes import agent_loops as agent_loop_routes
from backend.app.database.models import Base, User
from backend.app.database.session import get_db
from backend.app.main import app
from backend.app.services.agent_loop.artifacts import AgentLoopArtifactStore
from backend.app.services.agent_loop.service import AgentLoopService


@pytest.fixture()
def route_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db: Session = sessionmaker(bind=engine)()
    account = User(username="loop-api-operator", email="loop-api@example.test", password_hash="not-a-real-password")
    db.add(account)
    db.commit()
    db.refresh(account)

    artifacts = AgentLoopArtifactStore(
        state_dir=str(tmp_path / "state"),
        plan_dir=str(tmp_path / "plans"),
        log_dir=str(tmp_path / "logs"),
        report_dir=str(tmp_path / "reports"),
    )
    monkeypatch.setattr(agent_loop_routes, "service", lambda session: AgentLoopService(session, artifacts=artifacts))

    def override_db():
        yield db

    def override_user() -> User:
        return account

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
    db.close()
    Base.metadata.drop_all(engine)


def test_agent_loop_route_rejects_unauthenticated_requests() -> None:
    app.dependency_overrides.clear()
    with TestClient(app) as client:
        response = client.get("/api/v1/agent-loops")
    assert response.status_code == 401
    assert response.json()["detail"] == "Bearer token required"


def test_agent_loop_http_lifecycle_is_dry_run_and_hard_stop_protected(route_client: TestClient) -> None:
    created = route_client.post("/api/v1/agent-loops", json={"name": "Repository review loop", "config": {}})
    assert created.status_code == 201
    loop = created.json()
    assert loop["config"]["dry_run"] is True
    assert loop["config"]["repository"]["allow_merge"] is False
    assert loop["config"]["repository"]["allow_deploy"] is False
    assert loop["config"]["repository"]["allow_release"] is False

    loop_id = loop["id"]
    assert route_client.post(f"/api/v1/agent-loops/{loop_id}/start").json()["status"] == "scheduled"
    iteration = route_client.post(f"/api/v1/agent-loops/{loop_id}/run-dry")
    assert iteration.status_code == 200
    assert iteration.json()["dry_run"] is True
    assert iteration.json()["reflection"]["outcome"] == "review_required"
    assert iteration.json()["validation"]["executed"] is False

    listed = route_client.get(f"/api/v1/agent-loops/{loop_id}/iterations")
    assert listed.status_code == 200
    assert listed.json()["count"] == 1

    stopped = route_client.post(f"/api/v1/agent-loops/{loop_id}/hard-stop")
    assert stopped.status_code == 200
    assert stopped.json()["hard_stop"] is True
    assert stopped.json()["status"] == "stopped"

    denied_restart = route_client.post(f"/api/v1/agent-loops/{loop_id}/start")
    assert denied_restart.status_code == 400
    assert "Hard stop is active" in denied_restart.json()["detail"]
