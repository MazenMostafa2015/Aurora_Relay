from __future__ import annotations

import asyncio
import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database.models import Base, User
from backend.app.services.extensions.registry import ExtensionRegistry
from backend.app.services.extensions.service import ExtensionService, ExtensionServiceError


def _registry(tmp_path):
    root = tmp_path / "extensions"
    (root / "manifests").mkdir(parents=True)
    (root / "entries").mkdir()
    (root / "manifests" / "sample.tool.json").write_text(json.dumps({
        "id": "sample.tool",
        "display_name": "Sample tool",
        "version": "1.0.0",
        "description": "A local reviewed sandbox test extension.",
        "kind": "sandboxed_tool",
        "permissions": ["sandbox.execute"],
        "entrypoint": "sample.js",
    }), encoding="utf-8")
    (root / "entries" / "sample.js").write_text("console.log('ok');", encoding="utf-8")
    return ExtensionRegistry(root)


@pytest.fixture()
def extension_db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db: Session = sessionmaker(bind=engine)()
    user = User(username="extensions", email="extensions@example.test", password_hash="not-a-real-password")
    db.add(user)
    db.commit()
    db.refresh(user)
    yield db, user
    db.close()
    Base.metadata.drop_all(engine)


def test_local_extension_lifecycle_is_owner_scoped_and_disabled_by_default(extension_db, tmp_path) -> None:
    db, user = extension_db
    service = ExtensionService(db, registry=_registry(tmp_path))
    assert service.catalog(user)[0]["installed"] is False
    installed = service.install(user, "sample.tool")
    assert installed["enabled"] is False
    updated = service.update(user, "sample.tool", enabled=True, configuration={"theme": "dark"})
    assert updated["status"] == "ready"
    assert updated["configuration"] == {"theme": "dark"}
    assert service.list_installed(user)[0]["permissions"] == ["sandbox.execute"]


def test_extension_execution_fails_closed_when_docker_is_unavailable(extension_db, tmp_path) -> None:
    db, user = extension_db

    class UnavailableSandbox:
        async def initialize(self):
            raise RuntimeError("no Docker")

    service = ExtensionService(db, registry=_registry(tmp_path), sandbox_factory=UnavailableSandbox)
    service.install(user, "sample.tool")
    service.update(user, "sample.tool", enabled=True)
    result = asyncio.run(service.execute(user, "sample.tool"))
    assert result["state"] == "blocked"
    assert "host execution is not permitted" in result["message"]
    assert service.list_installed(user)[0]["status"] == "blocked"


def test_extension_rejects_unknown_or_remote_catalog_entries(extension_db, tmp_path) -> None:
    db, user = extension_db
    service = ExtensionService(db, registry=_registry(tmp_path))
    with pytest.raises(ExtensionServiceError, match="local registry"):
        service.install(user, "https://example.test/extension.json")
