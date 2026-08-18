"""Owner-scoped lifecycle service for reviewed local extensions."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...api.models import ExtensionKind, ExtensionManifest
from ...core.sandbox.config import SandboxConfig
from ...core.sandbox.manager import SandboxManager
from ...database.models import AuditLog, ExtensionInstallation, User
from .registry import ExtensionRegistry, ExtensionRegistryError


class ExtensionServiceError(RuntimeError):
    pass


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
        # This profile has no network, no added capabilities, a read-only root
        # filesystem, and bounded time/output inherited from SandboxConfig.
        return SandboxManager(SandboxConfig(timeout_seconds=15, max_timeout_seconds=15, enabled_languages=["python", "javascript"]))

    def _audit(self, user_id: str, event_type: str, record: ExtensionInstallation, details: dict[str, Any] | None = None) -> None:
        self.db.add(AuditLog(user_id=user_id, event_type=event_type, resource_type="extension", resource_id=record.id, details=details or {}))

    @staticmethod
    def _public(record: ExtensionInstallation) -> dict[str, Any]:
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

    def catalog(self, user: User) -> list[dict[str, Any]]:
        try:
            manifests = self.registry.catalog()
        except ExtensionRegistryError as exc:
            raise ExtensionServiceError(str(exc)) from exc
        records = {item.extension_id: item for item in self.db.scalars(select(ExtensionInstallation).where(ExtensionInstallation.user_id == user.id)).all()}
        return [manifest.model_dump() | {
            "installed": manifest.id in records,
            "enabled": records[manifest.id].enabled if manifest.id in records else False,
            "status": records[manifest.id].status if manifest.id in records else None,
            "configuration": records[manifest.id].configuration if manifest.id in records else {},
            "last_error": records[manifest.id].last_error if manifest.id in records else None,
        } for manifest in manifests.values()]

    def list_installed(self, user: User) -> list[dict[str, Any]]:
        records = self.db.scalars(select(ExtensionInstallation).where(ExtensionInstallation.user_id == user.id).order_by(ExtensionInstallation.created_at)).all()
        return [self._public(record) for record in records]

    def install(self, user: User, extension_id: str) -> dict[str, Any]:
        try:
            manifest = self.registry.manifest(extension_id)
        except ExtensionRegistryError as exc:
            raise ExtensionServiceError(str(exc)) from exc
        if self.db.scalar(select(ExtensionInstallation).where(ExtensionInstallation.user_id == user.id, ExtensionInstallation.extension_id == extension_id)):
            raise ExtensionServiceError("Extension is already installed")
        record = ExtensionInstallation(
            user_id=user.id,
            extension_id=manifest.id,
            display_name=manifest.display_name,
            version=manifest.version,
            kind=manifest.kind.value,
            manifest=manifest.model_dump(mode="json"),
            status="installed",
        )
        self.db.add(record)
        self.db.flush()
        self._audit(user.id, "extension.installed", record, {"extension_id": manifest.id, "kind": manifest.kind.value})
        self.db.commit()
        self.db.refresh(record)
        return self._public(record)

    def update(self, user: User, extension_id: str, *, enabled: bool | None = None, configuration: dict[str, Any] | None = None) -> dict[str, Any]:
        record = self._record(user, extension_id)
        try:
            manifest = self.registry.manifest(extension_id)
        except ExtensionRegistryError as exc:
            record.enabled = False
            record.status = "blocked"
            record.last_error = "The reviewed local manifest is no longer available"
            self._audit(user.id, "extension.blocked", record, {"reason": "manifest_unavailable"})
            self.db.commit()
            raise ExtensionServiceError(record.last_error) from exc
        if configuration is not None:
            record.configuration = configuration
        if enabled is not None:
            record.enabled = enabled
            record.status = "ready" if enabled else "disabled"
            record.last_error = None
        record.version = manifest.version
        record.display_name = manifest.display_name
        record.kind = manifest.kind.value
        record.manifest = manifest.model_dump(mode="json")
        self._audit(user.id, "extension.updated", record, {"enabled": enabled, "configuration_updated": configuration is not None})
        self.db.commit()
        self.db.refresh(record)
        return self._public(record)

    async def execute(self, user: User, extension_id: str) -> dict[str, Any]:
        record = self._record(user, extension_id)
        if not record.enabled or record.status != "ready":
            raise ExtensionServiceError("Enable this extension before requesting execution")
        try:
            manifest = self.registry.manifest(extension_id)
            entrypoint = self.registry.entrypoint_path(manifest)
        except ExtensionRegistryError as exc:
            raise ExtensionServiceError(str(exc)) from exc
        if manifest.kind is not ExtensionKind.SANDBOXED_TOOL or "sandbox.execute" not in {item.value for item in manifest.permissions}:
            raise ExtensionServiceError("This extension has no permitted sandbox execution capability")
        language = "javascript" if entrypoint.suffix == ".js" else "python"
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
            result = await sandbox.execute_code(container_id, entrypoint.read_text(encoding="utf-8"), language=language, timeout=15)
        finally:
            if container_id:
                await sandbox.destroy_sandbox(container_id)
        record.last_run_at = datetime.now(timezone.utc)
        record.status = "ready" if result["success"] else "failed"
        record.last_error = None if result["success"] else "Sandboxed extension execution failed"
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
