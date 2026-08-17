"""First-run secret provisioning for the packaged Aurora Relay backend.

This module is imported by the desktop launcher *before* importing app settings.
It creates exactly one per-user JWT secret, applies restrictive permissions, and
refuses to fall back to a shipped development value.
"""
from __future__ import annotations

import os
import secrets
import subprocess
from pathlib import Path


SECRET_FILE_NAME = "runtime.env"
SECRET_KEY_NAME = "JWT_SECRET_KEY"
MIN_SECRET_LENGTH = 64


def _read_secret(path: Path) -> str:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise RuntimeError(f"Unable to read protected runtime configuration: {exc}") from exc

    values: dict[str, str] = {}
    for line in lines:
        if not line or line.lstrip().startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if separator:
            values[key.strip()] = value.strip()

    secret = values.get(SECRET_KEY_NAME, "")
    if len(secret) < MIN_SECRET_LENGTH:
        raise RuntimeError("Runtime JWT secret is missing or too short; refusing to start.")
    return secret


def _harden_path(path: Path, *, is_directory: bool) -> None:
    """Restrict the secret directory/file to the interactive user.

    The launcher fails closed when Windows ACL hardening cannot be applied. This
    prevents silently storing a bearer-token signing secret in a world-readable
    file on an enterprise or multi-user workstation.
    """
    if os.name != "nt":
        path.chmod(0o700 if is_directory else 0o600)
        return

    user = os.environ.get("USERNAME")
    if not user:
        raise RuntimeError("Cannot determine the Windows user for runtime-secret ACLs.")

    command = ["icacls", str(path), "/inheritance:r", "/grant:r", f"{user}:(F)"]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "unknown icacls failure").strip()
        raise RuntimeError(f"Unable to protect runtime-secret ACLs: {detail}")


def provision_jwt_secret(config_dir: Path) -> str:
    """Load or atomically create the one per-install JWT signing secret."""
    config_dir.mkdir(parents=True, exist_ok=True)
    _harden_path(config_dir, is_directory=True)
    secret_path = config_dir / SECRET_FILE_NAME

    if secret_path.exists():
        _harden_path(secret_path, is_directory=False)
        return _read_secret(secret_path)

    secret = secrets.token_urlsafe(48)
    payload = f"{SECRET_KEY_NAME}={secret}\n"
    try:
        descriptor = os.open(str(secret_path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        _harden_path(secret_path, is_directory=False)
        return _read_secret(secret_path)
    except OSError as exc:
        raise RuntimeError(f"Unable to create protected runtime configuration: {exc}") from exc

    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())

    try:
        _harden_path(secret_path, is_directory=False)
    except Exception:
        secret_path.unlink(missing_ok=True)
        raise
    return secret


def load_runtime_secret(config_dir: Path) -> None:
    """Set the secret only for the current backend process; never print it."""
    secret = provision_jwt_secret(config_dir)
    existing = os.environ.get(SECRET_KEY_NAME)
    if existing and existing != secret:
        raise RuntimeError("An unexpected JWT_SECRET_KEY override was supplied; refusing to start.")
    os.environ[SECRET_KEY_NAME] = secret
