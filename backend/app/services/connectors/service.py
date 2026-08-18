"""Connector orchestration with strict credential and Revit mutation boundaries."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...database.models import AuditLog, Connector, ConnectorCredential, ConnectorOperation, User
from .adapters import AdapterResult, ConnectorAdapterError, GitHubAdapter, RevitMockAdapter
from .vault import CredentialVault, CredentialVaultError


class ConnectorServiceError(RuntimeError):
    pass


class ConnectorService:
    """User-scoped connector service.

    GitHub mutations are intentionally only exposed through explicit actions.
    Revit mutations are even stricter: ``plan_revit`` creates an immutable
    preview record and ``apply_revit`` accepts only an exact ``APPLY``
    confirmation for the same owner and connector.
    """

    def __init__(self, db: Session, *, vault: CredentialVault | None = None, github: GitHubAdapter | None = None, revit: RevitMockAdapter | None = None) -> None:
        self.db = db
        self.vault = vault or CredentialVault()
        self.github = github or GitHubAdapter()
        self.revit = revit or RevitMockAdapter()

    @staticmethod
    def _capabilities(provider: str) -> list[str]:
        if provider == "github":
            return list(GitHubAdapter.capabilities)
        if provider == "revit":
            return list(RevitMockAdapter.capabilities)
        return []

    @staticmethod
    def _public(connector: Connector) -> dict[str, Any]:
        return {
            "id": connector.id,
            "provider": connector.provider,
            "display_name": connector.display_name,
            "status": connector.status,
            "sort_order": connector.sort_order,
            "configuration": connector.configuration or {},
            "credential_configured": connector.credential_id is not None,
            "capabilities": ConnectorService._capabilities(connector.provider),
            "last_tested_at": connector.last_tested_at,
            "last_error": connector.last_error,
            "created_at": connector.created_at,
            "updated_at": connector.updated_at,
        }

    def _audit(self, user_id: str, event_type: str, connector: Connector, details: dict[str, Any] | None = None) -> None:
        self.db.add(AuditLog(user_id=user_id, event_type=event_type, resource_type="connector", resource_id=connector.id, details=details or {}))

    def list_connectors(self, user: User) -> list[dict[str, Any]]:
        rows = self.db.scalars(select(Connector).where(Connector.user_id == user.id).order_by(Connector.sort_order, Connector.created_at)).all()
        return [self._public(item) for item in rows]

    def get_connector(self, user: User, connector_id: str) -> Connector:
        connector = self.db.scalar(select(Connector).where(Connector.id == connector_id, Connector.user_id == user.id))
        if connector is None:
            raise ConnectorServiceError("Connector not found")
        return connector

    def create_connector(self, user: User, *, provider: str, display_name: str, configuration: dict[str, Any], credential: str | None = None, credential_label: str = "Primary credential") -> dict[str, Any]:
        if provider not in {"github", "revit"}:
            raise ConnectorServiceError("Unsupported connector provider")
        max_order = self.db.scalar(select(Connector.sort_order).where(Connector.user_id == user.id).order_by(Connector.sort_order.desc()).limit(1))
        credential_record = self._create_credential(user, provider, credential_label, credential) if credential else None
        connector = Connector(user_id=user.id, provider=provider, display_name=display_name.strip(), configuration=configuration, credential_id=credential_record.id if credential_record else None, status="not_configured", sort_order=(max_order or 0) + 1)
        self.db.add(connector)
        self.db.flush()
        self._audit(user.id, "connector.created", connector, {"provider": provider, "credential_configured": credential_record is not None})
        self.db.commit()
        self.db.refresh(connector)
        return self._public(connector)

    def update_connector(self, user: User, connector_id: str, *, display_name: str | None = None, configuration: dict[str, Any] | None = None, credential: str | None = None, credential_label: str | None = None, enabled: bool | None = None, sort_order: int | None = None) -> dict[str, Any]:
        connector = self.get_connector(user, connector_id)
        if display_name is not None:
            connector.display_name = display_name.strip()
        if configuration is not None:
            connector.configuration = configuration
        if credential is not None:
            record = self._create_credential(user, connector.provider, credential_label or "Updated credential", credential)
            connector.credential_id = record.id
        if enabled is not None:
            connector.status = "not_configured" if enabled else "disabled"
        if sort_order is not None and sort_order != connector.sort_order:
            peers = self.db.scalars(select(Connector).where(Connector.user_id == user.id, Connector.id != connector.id).order_by(Connector.sort_order)).all()
            target = max(1, min(sort_order, len(peers) + 1))
            old_order = connector.sort_order
            if target < old_order:
                for peer in peers:
                    if target <= peer.sort_order < old_order:
                        peer.sort_order += 1
            else:
                for peer in peers:
                    if old_order < peer.sort_order <= target:
                        peer.sort_order -= 1
            connector.sort_order = target
        self._audit(user.id, "connector.updated", connector, {"configuration_updated": configuration is not None, "credential_updated": credential is not None, "enabled": enabled, "sort_order": sort_order})
        self.db.commit()
        self.db.refresh(connector)
        return self._public(connector)

    def delete_connector(self, user: User, connector_id: str) -> None:
        connector = self.get_connector(user, connector_id)
        self._audit(user.id, "connector.deleted", connector, {"provider": connector.provider})
        self.db.delete(connector)
        self.db.commit()

    def _create_credential(self, user: User, provider: str, label: str, secret: str) -> ConnectorCredential:
        try:
            encrypted = self.vault.encrypt(secret)
        except CredentialVaultError as exc:
            raise ConnectorServiceError(str(exc)) from exc
        record = ConnectorCredential(user_id=user.id, provider=provider, label=label.strip(), ciphertext=encrypted)
        self.db.add(record)
        self.db.flush()
        return record

    def _credential_value(self, connector: Connector) -> str | None:
        if connector.credential is None:
            return None
        try:
            return self.vault.decrypt(connector.credential.ciphertext)
        except CredentialVaultError as exc:
            raise ConnectorServiceError(str(exc)) from exc

    async def test_connector(self, user: User, connector_id: str) -> dict[str, Any]:
        connector = self.get_connector(user, connector_id)
        connector.status = "testing"
        self.db.commit()
        try:
            if connector.provider == "github":
                result = await self.github.test(self._credential_value(connector) or "", connector.configuration or {})
            else:
                result = await self.revit.test(None, connector.configuration or {})
            connector.status = "connected"
            connector.last_error = None
            connector.last_tested_at = datetime.now(timezone.utc)
            self._audit(user.id, "connector.tested", connector, {"ok": True, "mode": result.data.get("mode")})
            self.db.commit()
            return {"ok": True, "provider": connector.provider, "message": result.message, "data": result.data}
        except (ConnectorAdapterError, ConnectorServiceError) as exc:
            connector.status = "needs_attention"
            connector.last_error = str(exc)[:500]
            connector.last_tested_at = datetime.now(timezone.utc)
            self._audit(user.id, "connector.tested", connector, {"ok": False, "reason": "provider_error"})
            self.db.commit()
            return {"ok": False, "provider": connector.provider, "message": str(exc), "data": {}}

    async def run_action(self, user: User, connector_id: str, action: str, input_data: dict[str, Any]) -> dict[str, Any]:
        connector = self.get_connector(user, connector_id)
        if connector.status == "disabled":
            raise ConnectorServiceError("This connector is disabled")
        if connector.provider != "github":
            raise ConnectorServiceError("Use the dedicated Revit plan and apply endpoints for model edits")
        try:
            result = await self.github.execute(action, input_data, self._credential_value(connector) or "", connector.configuration or {})
        except ConnectorAdapterError as exc:
            connector.status = "needs_attention"
            connector.last_error = str(exc)[:500]
            self._audit(user.id, "connector.action_failed", connector, {"action": action})
            self.db.commit()
            raise ConnectorServiceError(str(exc)) from exc
        connector.status = "connected"
        connector.last_error = None
        self._audit(user.id, "connector.action_completed", connector, {"action": action, "mutation": action in GitHubAdapter.mutation_actions})
        self.db.commit()
        return {"ok": True, "provider": connector.provider, "action": action, "message": result.message, "data": result.data}

    async def plan_revit(self, user: User, connector_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        connector = self.get_connector(user, connector_id)
        if connector.provider != "revit":
            raise ConnectorServiceError("The selected connector is not a Revit connector")
        if connector.status == "disabled":
            raise ConnectorServiceError("This connector is disabled")
        try:
            preview = await self.revit.preview(payload["operation"], payload)
        except ConnectorAdapterError as exc:
            raise ConnectorServiceError(str(exc)) from exc
        request_hash = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        operation = ConnectorOperation(connector_id=connector.id, user_id=user.id, provider="revit", operation_type=payload["operation"], state="planned", request_hash=request_hash, request_payload=payload, preview=preview.data)
        self.db.add(operation)
        self._audit(user.id, "revit.operation_planned", connector, {"operation_id": operation.id, "operation": payload["operation"], "mode": preview.data.get("mode")})
        self.db.commit()
        self.db.refresh(operation)
        return {"operation_id": operation.id, "state": "planned", "requires_confirmation": True, "preview": preview.data, "message": "Review the model preview, then confirm with APPLY to execute this transaction."}

    async def apply_revit(self, user: User, connector_id: str, operation_id: str, confirmation: str) -> dict[str, Any]:
        if confirmation != "APPLY":
            raise ConnectorServiceError("Revit changes require the explicit APPLY confirmation")
        connector = self.get_connector(user, connector_id)
        operation = self.db.scalar(select(ConnectorOperation).where(ConnectorOperation.id == operation_id, ConnectorOperation.connector_id == connector.id, ConnectorOperation.user_id == user.id))
        if operation is None:
            raise ConnectorServiceError("Planned Revit operation not found")
        if operation.state != "planned":
            raise ConnectorServiceError("This Revit operation has already been resolved")
        operation.confirmed_at = datetime.now(timezone.utc)
        try:
            result = await self.revit.apply(operation.operation_type, operation.request_payload)
            operation.state = "applied"
            operation.result = result.data
            operation.applied_at = datetime.now(timezone.utc)
            connector.status = "connected"
            connector.last_error = None
            self._audit(user.id, "revit.operation_applied", connector, {"operation_id": operation.id, "operation": operation.operation_type, "mode": result.data.get("mode")})
            self.db.commit()
            return {"operation_id": operation.id, "state": "applied", "message": result.message, "result": result.data}
        except ConnectorAdapterError as exc:
            operation.state = "failed"
            operation.error = str(exc)[:500]
            connector.status = "needs_attention"
            connector.last_error = str(exc)[:500]
            self._audit(user.id, "revit.operation_failed", connector, {"operation_id": operation.id, "operation": operation.operation_type})
            self.db.commit()
            return {"operation_id": operation.id, "state": "failed", "message": str(exc), "result": {}}
