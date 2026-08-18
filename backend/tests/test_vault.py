from __future__ import annotations

import os

import pytest
from cryptography.fernet import Fernet

from backend.app.services.connectors.vault import CredentialVault, CredentialVaultError


def test_locked_vault_is_fail_closed_and_has_no_secret_status(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AURORA_CONNECTOR_VAULT_LOCKED", "1")
    monkeypatch.setenv("AURORA_CONNECTOR_VAULT_BACKEND", "windows-credential-vault")
    vault = CredentialVault()

    assert vault.status().state == "locked"
    assert "key" not in vault.status().public()
    with pytest.raises(CredentialVaultError, match="locked"):
        vault.encrypt("ghp_must_not_be_stored")


def test_launcher_provided_key_preserves_existing_ciphertext_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    key = Fernet.generate_key().decode()
    monkeypatch.delenv("AURORA_CONNECTOR_VAULT_LOCKED", raising=False)
    monkeypatch.setenv("AURORA_CONNECTOR_VAULT_KEY", key)
    monkeypatch.setenv("AURORA_CONNECTOR_VAULT_BACKEND", "windows-credential-vault")
    vault = CredentialVault()

    encrypted = vault.encrypt("existing-connector-credential")
    assert encrypted != "existing-connector-credential"
    assert vault.decrypt(encrypted) == "existing-connector-credential"
    assert vault.status().backend == "windows-credential-vault"
    assert os.getenv("AURORA_CONNECTOR_VAULT_KEY") not in vault.status().public().values()
