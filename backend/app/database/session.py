from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from ..config.settings import settings


def _engine_kwargs(url: str) -> dict:
    if url.startswith("sqlite"):
        if url.startswith("sqlite:///./"):
            Path(url.removeprefix("sqlite:///./")).parent.mkdir(parents=True, exist_ok=True)
        return {"connect_args": {"check_same_thread": False}}
    return {"pool_pre_ping": True, "pool_size": settings.database_pool_size, "max_overflow": settings.database_max_overflow}


engine = create_engine(settings.sqlalchemy_url, **_engine_kwargs(settings.sqlalchemy_url))
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from .models import Base
    Base.metadata.create_all(bind=engine)
