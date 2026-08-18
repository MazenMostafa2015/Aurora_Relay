from __future__ import annotations

import pytest

from backend.app.core.mcp_servers.connector_management import server


def test_connector_mcp_refuses_unbound_processes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AURORA_MCP_USER_ID", raising=False)

    with pytest.raises(ValueError, match="not user-bound"):
        server._with_service()
