"""Connector service tests that use no live provider or desktop bridge."""
from __future__ import annotations

import asyncio
import json

import httpx
import pytest
from cryptography.fernet import Fernet
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database.models import Base, ConnectorCredential, User
from backend.app.services.connectors.adapters import GitHubAdapter, RevitMockAdapter
from backend.app.services.connectors.service import ConnectorService, ConnectorServiceError
from backend.app.services.connectors.vault import CredentialVault


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


def vault() -> CredentialVault:
    return CredentialVault(key=Fernet.generate_key().decode())


def test_connector_public_contract_redacts_the_encrypted_credential(db: Session) -> None:
    account = user(db)
    service = ConnectorService(db, vault=vault())

    public = service.create_connector(
        account,
        provider="github",
        display_name="Engineering GitHub",
        configuration={},
        credential="ghp_credential_that_must_not_leave_the_vault",
    )

    stored = db.scalar(select(ConnectorCredential))
    assert stored is not None
    assert stored.ciphertext != "ghp_credential_that_must_not_leave_the_vault"
    assert "credential" not in public
    assert public["credential_configured"] is True
    assert "ghp_credential_that_must_not_leave_the_vault" not in str(public)


def test_github_issue_action_uses_scoped_connector_and_never_echoes_token(db: Session) -> None:
    account = user(db)

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer ghp_local_test_token"
        assert request.url.path == "/repos/aurora/relay/issues"
        assert request.method == "POST"
        assert json.loads(request.content) == {"title": "Connector coverage", "body": "", "labels": []}
        return httpx.Response(201, json={"number": 42, "html_url": "https://example.test/aurora/relay/issues/42"})

    service = ConnectorService(
        db,
        vault=vault(),
        github=GitHubAdapter(transport=httpx.MockTransport(handler)),
    )
    connector = service.create_connector(account, provider="github", display_name="GitHub", configuration={"base_url": "https://example.test"}, credential="ghp_local_test_token")

    result = asyncio.run(service.run_action(account, connector["id"], "create_issue", {"owner": "aurora", "repo": "relay", "title": "Connector coverage"}))

    assert result["ok"] is True
    assert result["data"]["result"]["number"] == 42
    assert "ghp_local_test_token" not in str(result)


def test_revit_change_is_planned_before_it_can_be_applied_and_is_owner_scoped(db: Session) -> None:
    account = user(db)
    other = user(db, "other-operator")
    adapter = RevitMockAdapter()
    service = ConnectorService(db, vault=vault(), revit=adapter)
    connector = service.create_connector(account, provider="revit", display_name="Local Revit mock", configuration={})

    plan = asyncio.run(service.plan_revit(account, connector["id"], {"operation": "set_parameter", "transaction_name": "Set review comment", "set_parameter": {"element_id": 101, "parameter": "Comments", "value": "Reviewed"}}))

    assert plan["state"] == "planned"
    assert plan["requires_confirmation"] is True
    assert adapter.elements[101]["parameters"]["Comments"] == ""
    with pytest.raises(ConnectorServiceError, match="explicit APPLY"):
        asyncio.run(service.apply_revit(account, connector["id"], plan["operation_id"], "approve"))
    with pytest.raises(ConnectorServiceError, match="not found"):
        asyncio.run(service.apply_revit(other, connector["id"], plan["operation_id"], "APPLY"))

    result = asyncio.run(service.apply_revit(account, connector["id"], plan["operation_id"], "APPLY"))

    assert result["state"] == "applied"
    assert adapter.elements[101]["parameters"]["Comments"] == "Reviewed"
    with pytest.raises(ConnectorServiceError, match="already been resolved"):
        asyncio.run(service.apply_revit(account, connector["id"], plan["operation_id"], "APPLY"))


def test_connector_reordering_shifts_only_the_authenticated_users_inventory(db: Session) -> None:
    account = user(db)
    other = user(db, "other-operator")
    service = ConnectorService(db, vault=vault())
    first = service.create_connector(account, provider="github", display_name="First", configuration={})
    second = service.create_connector(account, provider="revit", display_name="Second", configuration={})
    other_connector = service.create_connector(other, provider="github", display_name="Other", configuration={})

    service.update_connector(account, second["id"], sort_order=1)

    ordered = service.list_connectors(account)
    assert [item["display_name"] for item in ordered] == ["Second", "First"]
    assert service.get_connector(other, other_connector["id"]).sort_order == 1
