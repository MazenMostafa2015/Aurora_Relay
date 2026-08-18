"""Secure replacement for backend/run.py in the packaged desktop backend."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from runtime_secrets import load_runtime_secret


def user_data_dir() -> Path:
    if sys.platform == "win32":
        root = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support"
    else:
        root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return root / "AuroraRelay"


def setup_environment() -> Path:
    data_dir = Path(os.environ.get("AURORA_DATA_DIR", user_data_dir())).expanduser().resolve()
    config_dir = Path(os.environ.get("AURORA_CONFIG_DIR", data_dir / "config")).expanduser().resolve()
    logs_dir = Path(os.environ.get("AURORA_LOGS_DIR", data_dir / "logs")).expanduser().resolve()
    for directory in (data_dir, config_dir, logs_dir):
        directory.mkdir(parents=True, exist_ok=True)

    os.environ.setdefault("AURORA_DATA_DIR", str(data_dir))
    os.environ.setdefault("AURORA_CONFIG_DIR", str(config_dir))
    os.environ.setdefault("AURORA_LOGS_DIR", str(logs_dir))
    os.environ.setdefault("DATABASE_URL", f"sqlite:///{data_dir / 'aurora-relay.db'}")
    os.environ.setdefault("DEBUG", "false")
    # pydantic-settings decodes complex environment values as JSON before field validation.
    os.environ.setdefault("ALLOWED_HOSTS", json.dumps(["127.0.0.1", "localhost"]))
    load_runtime_secret(config_dir)
    return data_dir


def main() -> None:
    setup_environment()
    import uvicorn
    from app.database.models import Base
    from app.database.session import engine
    from app.main import app

    Base.metadata.create_all(bind=engine)
    uvicorn.run(
        app,
        host=os.environ.get("AURORA_BIND_HOST", "127.0.0.1"),
        port=int(os.environ.get("AURORA_PORT", "0")),
        log_level=os.environ.get("LOG_LEVEL", "info").lower(),
        access_log=False,
    )


if __name__ == "__main__":
    main()
