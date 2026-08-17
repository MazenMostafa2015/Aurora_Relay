from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException, Request, WebSocket, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from ..config.settings import settings
from ..database.models import User
from ..database.session import get_db
from ..services.auth_service import AuthService

bearer = HTTPBearer(auto_error=False)


def get_token(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> str:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required")
    return credentials.credentials


def get_current_user(token: str = Depends(get_token), db: Session = Depends(get_db)) -> User:
    user = AuthService(db).authenticate_token(token)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    return user


def get_current_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin and user.id not in settings.admin_user_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


def get_app_state(request: Request) -> dict[str, Any]:
    return request.app.state.services


def get_ws_token(websocket: WebSocket) -> str | None:
    auth = websocket.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return websocket.query_params.get("token")
