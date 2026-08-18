"""Connector MCP facade.

MCP processes do not inherit browser sessions. The desktop launcher must bind
one process to one authenticated local user via ``AURORA_MCP_USER_ID``. The
facade refuses all actions without that context rather than guessing a user or
accepting credentials in tool arguments.
"""
from __future__ import annotations

import asyncio
import os
from typing import Any

from fastmcp import FastMCP

from ....database.models import User
from ....database.session import SessionLocal, init_db
from ....services.connectors import ConnectorService, ConnectorServiceError

mcp = FastMCP("Aurora-Relay-Connectors")


def _with_service() -> tuple[Any, User, ConnectorService]:
    user_id = os.getenv("AURORA_MCP_USER_ID")
    if not user_id:
        raise ValueError("Connector MCP is not user-bound. Start it through the authenticated Aurora Relay desktop launcher.")
    init_db()
    db = SessionLocal()
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        db.close()
        raise ValueError("The bound connector MCP user is unavailable")
    return db, user, ConnectorService(db)


def _close(db: Any) -> None:
    db.close()


@mcp.tool
def list_available_connectors() -> dict[str, Any]:
    """List the current desktop user’s connector status and allowed capabilities without exposing credentials."""
    db, user, service = _with_service()
    try:
        connectors = service.list_connectors(user)
        return {"connectors": connectors, "count": len(connectors), "credential_policy": "credentials stay in the Aurora Relay local vault"}
    finally:
        _close(db)


@mcp.tool
async def test_connector(connector_id: str) -> dict[str, Any]:
    """Test the named connector using its user-scoped vault reference; returns status but never a secret."""
    db, user, service = _with_service()
    try:
        return await service.test_connector(user, connector_id)
    except ConnectorServiceError as exc:
        return {"ok": False, "message": str(exc), "data": {}}
    finally:
        _close(db)


@mcp.tool
async def github_connector_action(connector_id: str, action: str, input: dict[str, Any]) -> dict[str, Any]:
    """Run a permitted GitHub repository, issue, PR, release, workflow, or content action through a configured connector."""
    db, user, service = _with_service()
    try:
        return await service.run_action(user, connector_id, action, input)
    except ConnectorServiceError as exc:
        return {"ok": False, "provider": "github", "action": action, "message": str(exc), "data": {}}
    finally:
        _close(db)


@mcp.tool
async def revit_plan_change(connector_id: str, operation: str, transaction_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Create a Revit model-edit preview. This never mutates a model and returns an operation ID requiring explicit APPLY confirmation."""
    db, user, service = _with_service()
    try:
        data = {"operation": operation, "transaction_name": transaction_name, **payload}
        return await service.plan_revit(user, connector_id, data)
    except ConnectorServiceError as exc:
        return {"state": "rejected", "message": str(exc), "preview": {}}
    finally:
        _close(db)


@mcp.tool
async def revit_apply_confirmed_change(connector_id: str, operation_id: str, confirmation: str) -> dict[str, Any]:
    """Apply exactly one previously previewed Revit operation. Only the literal confirmation APPLY is accepted."""
    db, user, service = _with_service()
    try:
        return await service.apply_revit(user, connector_id, operation_id, confirmation)
    except ConnectorServiceError as exc:
        return {"operation_id": operation_id, "state": "rejected", "message": str(exc), "result": {}}
    finally:
        _close(db)


if __name__ == "__main__":
    mcp.run()
