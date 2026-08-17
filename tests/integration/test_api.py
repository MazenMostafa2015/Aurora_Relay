from __future__ import annotations

import pytest
from starlette.websockets import WebSocketDisconnect

from tests.fixtures.test_data import unique_user


def test_health_and_openapi(client):
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] in {"healthy", "degraded"}
    assert client.get("/openapi.json").status_code == 200


def test_register_login_task_status_and_logout(client):
    user = unique_user("api")
    registered = client.post("/api/v1/auth/register", json={"username": user.username, "email": user.email, "password": user.password})
    assert registered.status_code in {200, 201}
    login = client.post("/api/v1/auth/login", json={"username": user.username, "password": user.password})
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    task = client.post("/api/v1/tasks", json={"order": "List the files in the workspace", "start_immediately": False}, headers=headers)
    assert task.status_code in {200, 201}
    task_id = task.json()["id"]
    status = client.get(f"/api/v1/tasks/{task_id}/status", headers=headers)
    assert status.status_code == 200
    assert "progress" in status.json()
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 200
    assert client.get("/api/v1/tasks", headers=headers).status_code == 401


def test_tool_and_server_discovery_are_authenticated(authenticated_client):
    tools = authenticated_client.get("/api/v1/tools")
    servers = authenticated_client.get("/api/v1/tools/servers")
    assert tools.status_code == 200
    assert {"tools", "count"}.issubset(tools.json())
    assert servers.status_code == 200
    assert {"servers", "connected"}.issubset(servers.json())


def test_websocket_rejects_missing_token(client):
    with pytest.raises(WebSocketDisconnect) as error:
        with client.websocket_connect("/ws"):
            pass
    assert error.value.code == 1008


def test_websocket_accepts_authenticated_subscription(client):
    user = unique_user("ws")
    client.post("/api/v1/auth/register", json={"username": user.username, "email": user.email, "password": user.password})
    token = client.post("/api/v1/auth/login", json={"username": user.username, "password": user.password}).json()["access_token"]
    with client.websocket_connect(f"/ws?token={token}") as websocket:
        websocket.send_json({"type": "subscribe_task", "task_id": "task-123"})
        event = websocket.receive_json()
        assert event["type"] == "status"
        assert event["payload"]["subscribed"] == "task-123"
