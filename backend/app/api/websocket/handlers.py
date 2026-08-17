from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from ..dependencies import get_ws_token
from ...services.auth_service import AuthService


class ConnectionManager:
    def __init__(self):
        self.connections: dict[str, set[WebSocket]] = defaultdict(set)
        self.subscriptions: dict[WebSocket, set[str]] = defaultdict(set)

    async def connect(self, websocket: WebSocket, user_id: str) -> None:
        await websocket.accept(); self.connections[user_id].add(websocket)

    def disconnect(self, websocket: WebSocket, user_id: str) -> None:
        self.connections.get(user_id, set()).discard(websocket); self.subscriptions.pop(websocket, None)

    async def publish(self, user_id: str, message: dict[str, Any], task_id: str | None = None) -> None:
        sockets = list(self.connections.get(user_id, set()))
        await asyncio.gather(*(socket.send_json(message) for socket in sockets if task_id is None or task_id in self.subscriptions[socket]), return_exceptions=True)

    async def handle(self, websocket: WebSocket, db) -> None:
        token = get_ws_token(websocket); user = AuthService(db).authenticate_token(token) if token else None
        if not user or not user.is_active:
            await websocket.close(code=1008); return
        await self.connect(websocket, user.id)
        try:
            while True:
                message = await websocket.receive_json()
                if message.get("type") == "subscribe_task" and message.get("task_id"):
                    self.subscriptions[websocket].add(message["task_id"])
                    await websocket.send_json({"type": "status", "payload": {"subscribed": message["task_id"]}})
        except WebSocketDisconnect:
            self.disconnect(websocket, user.id)

manager = ConnectionManager()
