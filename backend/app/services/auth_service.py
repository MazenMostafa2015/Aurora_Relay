from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config.settings import settings
from ..database.models import User, UserSession


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def hash_password(password: str) -> str:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        try:
            return bcrypt.checkpw(password.encode(), password_hash.encode())
        except (ValueError, TypeError):
            return False

    @staticmethod
    def token_hash(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    def create_access_token(self, user_id: str) -> tuple[str, int]:
        expires = settings.access_token_expire_seconds
        now = datetime.now(timezone.utc)
        token = jwt.encode({"sub": user_id, "type": "access", "iat": now, "exp": now + timedelta(seconds=expires)}, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
        return token, expires

    def decode_token(self, token: str) -> dict:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])

    def create_session(self, user: User, token: str, ip_address: str | None, user_agent: str | None) -> UserSession:
        session = UserSession(user_id=user.id, token_hash=self.token_hash(token), expires_at=datetime.now(timezone.utc) + timedelta(seconds=settings.access_token_expire_seconds), ip_address=ip_address, user_agent=user_agent)
        self.db.add(session)
        self.db.commit()
        return session

    def revoke_session(self, token: str) -> None:
        session = self.db.scalar(select(UserSession).where(UserSession.token_hash == self.token_hash(token)))
        if session:
            session.is_valid = False
            self.db.commit()

    def authenticate_token(self, token: str) -> User | None:
        try:
            payload = self.decode_token(token)
            user_id = payload.get("sub")
            session = self.db.scalar(select(UserSession).where(UserSession.token_hash == self.token_hash(token), UserSession.is_valid.is_(True)))
            if not session or session.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
                return None
            return self.db.get(User, user_id)
        except jwt.PyJWTError:
            return None
