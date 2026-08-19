"""Owner-scoped lifecycle service for fail-closed, verified local extensions."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...api.models import ExtensionKind, ExtensionManifest, ExtensionSignatureStatus
from ...core.sandbox.config import SandboxConfig
from ...core.sandbox.manager import SandboxManager
from ...database.models import AuditLog, ExtensionInstallation, User
from .registry import ExtensionRegistry, ExtensionRegistryError
from .signing import VerifiedExtensionPackage


class ExtensionServiceError(RuntimeError):
    pass


_STATUS_BY_ERROR_CODE = {
    "signature_missing": ExtensionSignatureStatus.UNSIGNED,
    "signer_untrusted": ExtensionSignatureStatus.UNTRUSTED,
    "signer_inactive": ExtensionSignatureStatus.UNTRUSTED,
    "signer_revoked": ExtensionSignatureStatus.REVOKED,
    "signature_invalid": ExtensionSignatureStatus.TAMPERED,
    "payload_index": ExtensionSignatureStatus.TAMPERED,
    "payload_digest": ExtensionSignatureStatus.TAMPERED,
    "bootstrap_unavailable": ExtensionSignatureStatus.TRUST_UNAVAILABLE,
    "keyring_unavailable": ExtensionSignatureStatus.TRUST_UNAVAILABLE,
    "keyring_tampered": ExtensionSignatureStatus.TRUST_UNAVAILABLE,
    "keyring_invalid": ExtensionSignatureStatus.TRUST_UNAVAILABLE,
}


class ExtensionService:
    """Lifecycle controls that never fetch, unpack, or execute remote packages."""

    def __init__(
        self,
        db: Session,
        *,
        registry: ExtensionRegistry | None = None,
        sandbox_factory: Callable[[], SandboxManager] | None = None,
    ) -> None:
        self.db = db
        self.registry = registry or ExtensionRegistry()
        self.sandbox_factory = sandbox_factory or self._sandbox

    @staticmethod
    def _sandbox() -> SandboxManager:
        return SandboxManager(SandboxConfig(timeout_seconds=15, max_timeout_seconds=15, enabled_languages=["python", "javascript"]))

    def _audit(self, user_id: str, event_type: str, record: ExtensionInstallation, details: dict[str, Any] | None = None) -> None:
        self.db.add(AuditLog(user_id=user_id, event_type=event_type, resource_type="extension", resource_id=record.id, details=details or {}))

    @staticmethod
    def _signature_status(record: ExtensionInstallation) -> ExtensionSignatureStatus:
        try:
            return ExtensionSignatureStatus(record.signature_status)
        except ValueError:
            return ExtensionSignatureStatus.INVALID

    @classmethod
    def _public(cls, record: ExtensionInstallation) -> dict[str, Any]:
        manifest = ExtensionManifest.model_validate(record.manifest or {})
        return {
            "id": record.id,
            "extension_id": record.extension_id,
            "display_name": record.display_name,
            "version": record.version,
            "description": manifest.description,
            "kind": record.kind,
            "permissions": manifest.permissions,
            "enabled": record.enabled,
            "status": record.status,
            "signature_status": cls._signature_status(record),
            "signer_key_id": record.signer_key_id,
            "package_sha256": record.package_sha256,
            "verified_at": record.verified_at,
            "configuration": record.configuration or {},
            "last_error": record.last_error,
            "last_run_at": record.last_run_at,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
        }

    def _record(self, user: User, extension_id: str) -> ExtensionInstallation:
        record = self.db.scalar(select(ExtensionInstallation).where(ExtensionInstallation.user_id == user.id, ExtensionInstallation.extension_id == extension_id))
        if record is None:
            raise ExtensionServiceError("Extension is not installed")
        return record

    @staticmethod
    def _manifest_payload(package: VerifiedExtensionPackage) -> dict[str, Any]:
        return package.manifest.model_dump(mode="json")

    def _apply_verified_identity(self, record: ExtensionInstallation, package: VerifiedExtensionPackage) -> None:
        record.version = package.manifest.version
        record.display_name = package.manifest.display_name
        record.kind = package.manifest.kind.value
        record.manifest = self._manifest_payload(package)
        record.signature_status = ExtensionSignatureStatus.VERIFIED.value
        record.signer_key_id = package.signer_key_id
        record.package_sha256 = package.package_sha256
        record.manifest_sha256 = package.manifest_sha256
        record.verified_at = package.verified_at
        record.verification_error_code = None

    def _block(self, user: User, record: ExtensionInstallation, *, code: str) -> None:
        status = _STATUS_BY_ERROR_CODE.get(code, ExtensionSignatureStatus.INVALID)
        record.enabled = False
        record.status = "blocked"
        record.signature_status = status.value
        record.verification_error_code = code[:64]
        record.last_error = "Extension verification failed; package use is blocked"
        self._audit(user.id, "extension.blocked", record, {"reason": code})
        self.db.commit()

    def _verified(self, user: User, extension_id: str, record: ExtensionInstallation | None = None) -> VerifiedExtensionPackage:
        try:
            package = self.registry.package(extension_id)
        except ExtensionRegistryError as exc:
            if record is not None:
                self._block(user, record, code=exc.code)
            raise ExtensionServiceError("Extension verification failed; package use is blocked") from exc
        if record is not None and any((
            record.extension_id != package.manifest.id,
            record.package_sha256 != package.package_sha256,
            record.manifest_sha256 != package.manifest_sha256,
            record.signer_key_id != package.signer_key_id,
        )):
            self._block(user, record, code="identity_changed")
            raise ExtensionServiceError("Extension verification failed; package use is blocked")
        return package

    def catalog(self, user: User) -> list[dict[str, Any]]:
        try:
            packages = self.registry.catalog()
        except ExtensionRegistryError as exc:
            raise ExtensionServiceError("Extension verification failed; package use is blocked") from exc
        records = {item.extension_id: item for item in self.db.scalars(select(ExtensionInstallation).where(ExtensionInstallation.user_id == user.id)).all()}
        return [
            package.manifest.model_dump(mode="json") | {
                "installed": package.manifest.id in records,
                "enabled": records[package.manifest.id].enabled if package.manifest.id in records else False,
                "status": records[package.manifest.id].status if package.manifest.id in records else None,
                "configuration": records[package.manifest.id].configuration if package.manifest.id in records else {},
                "last_error": records[package.manifest.id].last_error if package.manifest.id in records else None,
                "signature_status": ExtensionSignatureStatus.VERIFIED,
                "signer_key_id": package.signer_key_id,
                "package_sha256": package.package_sha256,
                "verified_at": package.verified_at,
            }
            for package in packages.values()
        ]

    def list_installed(self, user: User) -> list[dict[str, Any]]:
        records = self.db.scalars(select(ExtensionInstallation).where(ExtensionInstallation.user_id == user.id).order_by(ExtensionInstallation.created_at)).all()
        return [self._public(record) for record in records]

    def install(self, user: User, extension_id: str) -> dict[str, Any]:
        package = self._verified(user, extension_id)
        if self.db.scalar(select(ExtensionInstallation).where(ExtensionInstallation.user_id == user.id, ExtensionInstallation.extension_id == extension_id)):
            raise ExtensionServiceError("Extension is already installed")
        record = ExtensionInstallation(
            user_id=user.id,
            extension_id=package.manifest.id,
            display_name=package.manifest.display_name,
            version=package.manifest.version,
            kind=package.manifest.kind.value,
            manifest=self._manifest_payload(package),
            signature_status=ExtensionSignatureStatus.VERIFIED.value,
            signer_key_id=package.signer_key_id,
            package_sha256=package.package_sha256,
            manifest_sha256=package.manifest_sha256,
            verified_at=package.verified_at,
            status="installed",
        )
        self.db.add(record)
        self.db.flush()
        self._audit(user.id, "extension.installed", record, {"extension_id": package.manifest.id, "signer_key_id": package.signer_key_id})
        self.db.commit()
        self.db.refresh(record)
        return self._public(record)

    def update(self, user: User, extension_id: str, *, enabled: bool | None = None, configuration: dict[str, Any] | None = None) -> dict[str, Any]:
        record = self._record(user, extension_id)
        package = self._verified(user, extension_id, record)
        if configuration is not None:
            record.configuration = configuration
        if enabled is not None:
            record.enabled = enabled
            record.status = "ready" if enabled else "disabled"
            record.last_error = None
        self._apply_verified_identity(record, package)
        self._audit(user.id, "extension.updated", record, {"enabled": enabled, "configuration_updated": configuration is not None})
        self.db.commit()
        self.db.refresh(record)
        return self._public(record)

    async def execute(self, user: User, extension_id: str) -> dict[str, Any]:
        record = self._record(user, extension_id)
        if not record.enabled or record.status != "ready" or self._signature_status(record) is not ExtensionSignatureStatus.VERIFIED:
            raise ExtensionServiceError("Enable a verified extension before requesting execution")
        package = self._verified(user, extension_id, record)
        manifest = package.manifest
        if manifest.kind is not ExtensionKind.SANDBOXED_TOOL or "sandbox.execute" not in {item.value for item in manifest.permissions}:
            raise ExtensionServiceError("This extension has no permitted sandbox execution capability")
        try:
            source = package.entrypoint_bytes().decode("utf-8")
        except UnicodeDecodeError:
            self._block(user, record, code="entrypoint_encoding")
            raise ExtensionServiceError("Extension verification failed; package use is blocked")
        language = "javascript" if manifest.entrypoint and manifest.entrypoint.endswith(".js") else "python"
        sandbox = self.sandbox_factory()
        try:
            await sandbox.initialize()
        except Exception:
            record.status = "blocked"
            record.last_error = "Docker sandbox is unavailable; host execution is not permitted"
            self._audit(user.id, "extension.execution_blocked", record, {"reason": "sandbox_unavailable"})
            self.db.commit()
            return {"extension_id": extension_id, "state": "blocked", "message": record.last_error, "exit_code": None, "stdout": "", "stderr": ""}
        container_id: str | None = None
        try:
            container_id = await sandbox.create_sandbox(language=language)
            result = await sandbox.execute_code(container_id, source, language=language, timeout=15)
        finally:
            if container_id:
                await sandbox.destroy_sandbox(container_id)
        record.last_run_at = datetime.now(UTC)
        record.status = "ready" if result["success"] else "failed"
        record.last_error = None if result["success"] else "Sandboxed extension execution failed"
        self._apply_verified_identity(record, package)
        self._audit(user.id, "extension.executed", record, {"success": result["success"], "exit_code": result["exit_code"], "language": language})
        self.db.commit()
        return {
            "extension_id": extension_id,
            "state": "completed" if result["success"] else "failed",
            "message": "Extension executed in the Docker sandbox" if result["success"] else "Extension execution failed in the Docker sandbox",
            "exit_code": result["exit_code"],
            "stdout": result["stdout"],
            "stderr": result["stderr"],
        }
