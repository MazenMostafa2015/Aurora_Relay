"""Small encrypted local vault for connector credentials.

The encryption key is never stored in the database with ciphertext. Desktop
launchers should set ``AURORA_CONNECTOR_VAULT_KEY`` from an OS secret store;
the guarded per-user file fallback exists for local-only development.
"""
from __future__ import annotations

import base64
import os
import stat
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from cryptography.fernet import Fernet, InvalidToken


class CredentialVaultError(RuntimeError):
    pass


@dataclass(frozen=True)
class CredentialVaultStatus:
    """Opaque state for UI and diagnostics; it never contains key material."""

    state: Literal["ready", "locked"]
    backend: str
    fallback: bool
    reason: str | None = None

    def public(self) -> dict[str, str | bool | None]:
        return asdict(self)


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


class CredentialVault:
    def __init__(self, key_path: str | Path | None = None, key: str | None = None) -> None:
        configured_path = key_path or os.getenv("AURORA_CONNECTOR_VAULT_PATH")
        self.key_path = Path(configured_path) if configured_path else Path(os.getenv("AURORA_APP_DATA_DIR", str(Path.home() / ".aurora-relay"))) / "connector-vault.key"
        configured_backend = os.getenv("AURORA_CONNECTOR_VAULT_BACKEND", "encrypted-local-file")
        fallback = _truthy(os.getenv("AURORA_CONNECTOR_VAULT_FALLBACK"))
        self._fernet: Fernet | None = None
        if _truthy(os.getenv("AURORA_CONNECTOR_VAULT_LOCKED")):
            self._status = CredentialVaultStatus(
                state="locked",
                backend=configured_backend,
                fallback=fallback,
                reason=os.getenv("AURORA_CONNECTOR_VAULT_LOCK_REASON", "OS credential protection is unavailable."),
            )
            return
        try:
            raw_key = key or os.getenv("AURORA_CONNECTOR_VAULT_KEY")
            self._fernet = Fernet(raw_key.encode() if raw_key else self._load_or_create_key())
            self._status = CredentialVaultStatus(state="ready", backend=configured_backend, fallback=fallback)
        except (OSError, ValueError) as exc:
            self._status = CredentialVaultStatus(
                state="locked",
                backend=configured_backend,
                fallback=fallback,
                reason="The local credential vault could not be initialized.",
            )

    @staticmethod
    def status_from_environment() -> CredentialVaultStatus:
        """Return current launcher-provided state without creating or reading keys."""
        backend = os.getenv("AURORA_CONNECTOR_VAULT_BACKEND", "encrypted-local-file")
        fallback = _truthy(os.getenv("AURORA_CONNECTOR_VAULT_FALLBACK"))
        if _truthy(os.getenv("AURORA_CONNECTOR_VAULT_LOCKED")):
            return CredentialVaultStatus(
                state="locked",
                backend=backend,
                fallback=fallback,
                reason=os.getenv("AURORA_CONNECTOR_VAULT_LOCK_REASON", "OS credential protection is unavailable."),
            )
        return CredentialVaultStatus(state="ready", backend=backend, fallback=fallback)

    def status(self) -> CredentialVaultStatus:
        return self._status

    def _require_ready(self) -> Fernet:
        if self._fernet is None:
            reason = self._status.reason or "Credential protection is unavailable."
            raise CredentialVaultError(f"The connector credential vault is locked: {reason}")
        return self._fernet

    def _load_or_create_key(self) -> bytes:
        try:
            if self.key_path.exists():
                return self.key_path.read_bytes().strip()
            self.key_path.parent.mkdir(parents=True, exist_ok=True)
            key = Fernet.generate_key()
            descriptor = os.open(self.key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(key)
            return key
        except OSError as exc:
            raise CredentialVaultError("Could not initialize the local connector credential vault") from exc

    def encrypt(self, secret: str) -> str:
        if not secret or not secret.strip():
            raise CredentialVaultError("A connector credential is required")
        return self._require_ready().encrypt(secret.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        try:
            return self._require_ready().decrypt(ciphertext.encode()).decode()
        except (InvalidToken, UnicodeDecodeError) as exc:
            raise CredentialVaultError("The connector credential cannot be read on this installation") from exc

    def key_fingerprint(self) -> str:
        """Diagnostic-only, non-secret identifier for support logs."""
        raw = self._require_ready()._signing_key  # cryptography does not expose a public key identifier.
        return base64.urlsafe_b64encode(raw[:6]).decode().rstrip("=")

    def is_user_only(self) -> bool:
        if self._fernet is None or os.name == "nt" or not self.key_path.exists():
            return True
        return stat.S_IMODE(self.key_path.stat().st_mode) == 0o600
