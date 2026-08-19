from __future__ import annotations

import asyncio
import hashlib
import json
import zipfile

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database.models import Base, User
from backend.app.services.extensions.registry import ExtensionRegistry, ExtensionRegistryError
from backend.app.services.extensions.service import ExtensionService, ExtensionServiceError
from backend.app.services.extensions.signing import (
    ExtensionPackageVerifier,
    ExtensionSignatureStatus,
    b64url_encode,
    canonical_json,
    key_id_from_public_key,
)


def _public(private: Ed25519PrivateKey) -> tuple[str, bytes]:
    raw = private.public_key().public_bytes_raw()
    return key_id_from_public_key(raw), raw


def _write_json(path, value) -> None:
    path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")


def _fixture_package(tmp_path, *, signer_state: str = "active", unsigned: bool = False, tampered: bool = False):
    root = tmp_path / "extensions"
    packages = root / "packages"
    trust = root / "trust"
    packages.mkdir(parents=True)
    trust.mkdir()
    bootstrap = Ed25519PrivateKey.generate()
    signer = Ed25519PrivateKey.generate()
    bootstrap_id, bootstrap_raw = _public(bootstrap)
    signer_id, signer_raw = _public(signer)
    _write_json(trust / "bootstrap.json", {"key_id": bootstrap_id, "public_key": b64url_encode(bootstrap_raw)})
    keyring = {
        "schema": "aurora-keyring/v1",
        "generation": 1,
        "keys": [{"key_id": signer_id, "public_key": b64url_encode(signer_raw), "state": signer_state, "usages": ["package"]}],
    }
    keyring["signature"] = {"format": "aurora-ed25519/v1", "key_id": bootstrap_id, "signature": b64url_encode(bootstrap.sign(canonical_json(keyring)))}
    _write_json(trust / "keyring.json", keyring)
    source = b"console.log('ok');\n"
    manifest = {
        "package_format": "aurora-extension/v1",
        "id": "sample.tool",
        "display_name": "Sample tool",
        "version": "1.0.0",
        "description": "A local reviewed sandbox test extension.",
        "kind": "sandboxed_tool",
        "permissions": ["sandbox.execute"],
        "entrypoint": "payload/sample.js",
        "files": [{"path": "payload/sample.js", "sha256": hashlib.sha256(source).hexdigest(), "size": len(source)}],
    }
    signed_manifest = dict(manifest)
    if tampered:
        manifest["display_name"] = "Tampered extension"
    signature = {"format": "aurora-ed25519/v1", "key_id": signer_id, "signature": b64url_encode(signer.sign(canonical_json(signed_manifest)))}
    package = packages / "sample.tool.aurx"
    with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", canonical_json(manifest))
        if not unsigned:
            archive.writestr("manifest.json.sig", canonical_json(signature))
        archive.writestr("payload/sample.js", source)
    return root, package


def _registry(tmp_path) -> ExtensionRegistry:
    root, _ = _fixture_package(tmp_path)
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


def test_verified_local_extension_lifecycle_is_owner_scoped_and_disabled_by_default(extension_db, tmp_path) -> None:
    db, user = extension_db
    service = ExtensionService(db, registry=_registry(tmp_path))
    catalog_item = service.catalog(user)[0]
    assert catalog_item["installed"] is False
    assert catalog_item["signature_status"] is ExtensionSignatureStatus.VERIFIED
    installed = service.install(user, "sample.tool")
    assert installed["enabled"] is False
    assert installed["signature_status"] is ExtensionSignatureStatus.VERIFIED
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


def test_unsigned_package_is_rejected_before_catalog_or_install(tmp_path) -> None:
    root, package = _fixture_package(tmp_path, unsigned=True)
    with pytest.raises(ExtensionRegistryError, match="unsigned"):
        ExtensionRegistry(root).catalog()
    with pytest.raises(Exception) as error:
        ExtensionPackageVerifier(root / "trust").verify(package)
    assert error.value.status is ExtensionSignatureStatus.UNSIGNED


def test_tampered_manifest_is_rejected_before_catalog_or_install(tmp_path) -> None:
    root, package = _fixture_package(tmp_path, tampered=True)
    with pytest.raises(Exception) as error:
        ExtensionPackageVerifier(root / "trust").verify(package)
    assert error.value.status is ExtensionSignatureStatus.TAMPERED


def test_revoked_signer_is_rejected_before_catalog_or_install(tmp_path) -> None:
    root, package = _fixture_package(tmp_path, signer_state="revoked")
    with pytest.raises(Exception) as error:
        ExtensionPackageVerifier(root / "trust").verify(package)
    assert error.value.status is ExtensionSignatureStatus.REVOKED


def test_extension_rejects_unknown_or_remote_catalog_entries(extension_db, tmp_path) -> None:
    db, user = extension_db
    service = ExtensionService(db, registry=_registry(tmp_path))
    with pytest.raises(ExtensionServiceError, match="verification failed"):
        service.install(user, "https://example.test/extension.json")
