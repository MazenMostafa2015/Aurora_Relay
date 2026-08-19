"""Fail-closed verification for Aurora Relay `.aurx` extension packages.

The backend only receives trusted public metadata and never creates, imports, or
exports publisher private keys. Package verification consumes one immutable
archive buffer so executable bytes cannot change between verification and
Docker staging.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import rfc8785
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from ...api.models import ExtensionManifest, ExtensionSignatureStatus


MAX_PACKAGE_BYTES = 12 * 1024 * 1024
MAX_ENTRY_BYTES = 10 * 1024 * 1024
MAX_MANIFEST_BYTES = 128 * 1024
MAX_SIGNATURE_BYTES = 8 * 1024
MAX_COMPRESSION_RATIO = 100
_META_FILES = {"manifest.json", "manifest.json.sig"}


class PackageVerificationError(RuntimeError):
    """A safe, categorized failure that must block package use."""

    def __init__(self, status: ExtensionSignatureStatus, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code


@dataclass(frozen=True)
class TrustedSigner:
    key_id: str
    public_key: bytes
    usages: frozenset[str]
    state: str


@dataclass(frozen=True)
class VerifiedExtensionPackage:
    manifest: ExtensionManifest
    package_path: Path
    package_sha256: str
    manifest_sha256: str
    signer_key_id: str
    verified_at: datetime
    payload_bytes: dict[str, bytes]

    def entrypoint_bytes(self) -> bytes:
        if not self.manifest.entrypoint:
            raise PackageVerificationError(ExtensionSignatureStatus.INVALID, "missing_entrypoint", "The verified package has no executable entrypoint")
        try:
            return self.payload_bytes[self.manifest.entrypoint]
        except KeyError as exc:
            raise PackageVerificationError(ExtensionSignatureStatus.TAMPERED, "entrypoint_unavailable", "The verified package entrypoint is unavailable") from exc


def b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def b64url_decode(value: str) -> bytes:
    if not isinstance(value, str) or not value or any(char.isspace() for char in value):
        raise ValueError("Invalid base64url value")
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def key_id_from_public_key(public_key: bytes) -> str:
    if len(public_key) != 32:
        raise ValueError("Ed25519 public keys must be 32 bytes")
    return f"ed25519:sha256:{b64url_encode(hashlib.sha256(public_key).digest())}"


def canonical_json(value: Any) -> bytes:
    """Return RFC 8785 bytes; ordinary json.dumps is never a signing substitute."""
    try:
        return rfc8785.dumps(value)
    except Exception as exc:
        raise PackageVerificationError(ExtensionSignatureStatus.INVALID, "noncanonical_json", "Package metadata cannot be canonicalized") from exc


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON object key")
        result[key] = value
    return result


def strict_json(data: bytes, *, limit: int) -> dict[str, Any]:
    if not data or len(data) > limit:
        raise PackageVerificationError(ExtensionSignatureStatus.INVALID, "metadata_size", "Package metadata exceeds the allowed size")
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=_no_duplicate_keys)
    except (UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
        raise PackageVerificationError(ExtensionSignatureStatus.INVALID, "invalid_json", "Package metadata is invalid") from exc
    if not isinstance(value, dict):
        raise PackageVerificationError(ExtensionSignatureStatus.INVALID, "invalid_json", "Package metadata must be an object")
    return value


def _safe_archive_name(name: str) -> bool:
    return bool(name) and not name.endswith("/") and not name.startswith(("/", "\\")) and "\\" not in name and "\x00" not in name and all(part not in {"", ".", ".."} for part in name.split("/"))


class TrustedKeyring:
    """Loads a bootstrap-pinned, signed, offline package-signer keyring."""

    def __init__(self, trust_dir: str | Path) -> None:
        self.trust_dir = Path(trust_dir)

    def _load_bootstrap(self) -> tuple[str, bytes]:
        try:
            payload = strict_json((self.trust_dir / "bootstrap.json").read_bytes(), limit=MAX_SIGNATURE_BYTES)
            raw = b64url_decode(str(payload["public_key"]))
            key_id = str(payload["key_id"])
            if key_id != key_id_from_public_key(raw):
                raise ValueError("Bootstrap key id mismatch")
            return key_id, raw
        except (OSError, KeyError, TypeError, ValueError, PackageVerificationError) as exc:
            raise PackageVerificationError(ExtensionSignatureStatus.TRUST_UNAVAILABLE, "bootstrap_unavailable", "Trusted extension signer configuration is unavailable") from exc

    def load(self) -> dict[str, TrustedSigner]:
        bootstrap_id, bootstrap = self._load_bootstrap()
        try:
            keyring = strict_json((self.trust_dir / "keyring.json").read_bytes(), limit=MAX_MANIFEST_BYTES)
            envelope = keyring.pop("signature")
            if not isinstance(envelope, dict) or envelope.get("format") != "aurora-ed25519/v1" or envelope.get("key_id") != bootstrap_id:
                raise ValueError("Invalid keyring signature envelope")
            Ed25519PublicKey.from_public_bytes(bootstrap).verify(b64url_decode(str(envelope["signature"])), canonical_json(keyring))
            if keyring.get("schema") != "aurora-keyring/v1" or not isinstance(keyring.get("generation"), int) or not isinstance(keyring.get("keys"), list):
                raise ValueError("Invalid keyring schema")
        except InvalidSignature as exc:
            raise PackageVerificationError(ExtensionSignatureStatus.TRUST_UNAVAILABLE, "keyring_tampered", "Trusted extension signer configuration is unavailable") from exc
        except (OSError, KeyError, TypeError, ValueError, PackageVerificationError) as exc:
            raise PackageVerificationError(ExtensionSignatureStatus.TRUST_UNAVAILABLE, "keyring_unavailable", "Trusted extension signer configuration is unavailable") from exc
        trusted: dict[str, TrustedSigner] = {}
        for item in keyring["keys"]:
            if not isinstance(item, dict):
                raise PackageVerificationError(ExtensionSignatureStatus.TRUST_UNAVAILABLE, "keyring_invalid", "Trusted extension signer configuration is unavailable")
            try:
                raw = b64url_decode(str(item["public_key"]))
                key_id = str(item["key_id"])
                usages = frozenset(str(value) for value in item["usages"])
                state = str(item["state"])
                if key_id != key_id_from_public_key(raw) or not usages or state not in {"active", "retired", "revoked"}:
                    raise ValueError("Invalid signer")
                trusted[key_id] = TrustedSigner(key_id=key_id, public_key=raw, usages=usages, state=state)
            except (KeyError, TypeError, ValueError) as exc:
                raise PackageVerificationError(ExtensionSignatureStatus.TRUST_UNAVAILABLE, "keyring_invalid", "Trusted extension signer configuration is unavailable") from exc
        return trusted


class ExtensionPackageVerifier:
    """Defensively parses and verifies a local `.aurx` archive."""

    def __init__(self, trust_dir: str | Path) -> None:
        self.keyring = TrustedKeyring(trust_dir)

    def verify(self, package_path: str | Path) -> VerifiedExtensionPackage:
        package = Path(package_path).resolve()
        try:
            raw_package = package.read_bytes()
        except OSError as exc:
            raise PackageVerificationError(ExtensionSignatureStatus.INVALID, "package_unavailable", "Extension package is unavailable") from exc
        if not raw_package or len(raw_package) > MAX_PACKAGE_BYTES:
            raise PackageVerificationError(ExtensionSignatureStatus.INVALID, "package_size", "Extension package exceeds the allowed size")
        try:
            archive = zipfile.ZipFile(io.BytesIO(raw_package))
        except (OSError, zipfile.BadZipFile) as exc:
            raise PackageVerificationError(ExtensionSignatureStatus.INVALID, "invalid_archive", "Extension package is not a valid archive") from exc
        try:
            entries = archive.infolist()
            names = [entry.filename for entry in entries]
            if not entries or len(names) != len(set(names)) or any(not _safe_archive_name(name) for name in names):
                raise PackageVerificationError(ExtensionSignatureStatus.INVALID, "archive_paths", "Extension package contains invalid archive paths")
            if set(_META_FILES) - set(names) or any(entry.flag_bits & 0x1 for entry in entries):
                raise PackageVerificationError(ExtensionSignatureStatus.UNSIGNED, "signature_missing", "Extension package is unsigned")
            for entry in entries:
                if entry.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED} or entry.file_size > MAX_ENTRY_BYTES:
                    raise PackageVerificationError(ExtensionSignatureStatus.INVALID, "archive_limits", "Extension package exceeds allowed archive limits")
                if entry.file_size and entry.compress_size and entry.file_size / entry.compress_size > MAX_COMPRESSION_RATIO:
                    raise PackageVerificationError(ExtensionSignatureStatus.INVALID, "archive_ratio", "Extension package exceeds allowed archive limits")
            manifest_data = strict_json(archive.read("manifest.json"), limit=MAX_MANIFEST_BYTES)
            signature = strict_json(archive.read("manifest.json.sig"), limit=MAX_SIGNATURE_BYTES)
            if set(signature) != {"format", "key_id", "signature"} or signature["format"] != "aurora-ed25519/v1":
                raise PackageVerificationError(ExtensionSignatureStatus.INVALID, "signature_envelope", "Extension package signature is invalid")
            manifest = ExtensionManifest.model_validate(manifest_data)
            canonical_manifest = canonical_json(manifest_data)
            signers = self.keyring.load()
            signer = signers.get(str(signature["key_id"]))
            if signer is None:
                raise PackageVerificationError(ExtensionSignatureStatus.UNTRUSTED, "signer_untrusted", "Extension signer is not trusted")
            if signer.state == "revoked":
                raise PackageVerificationError(ExtensionSignatureStatus.REVOKED, "signer_revoked", "Extension signer has been revoked")
            if signer.state != "active" or "package" not in signer.usages:
                raise PackageVerificationError(ExtensionSignatureStatus.UNTRUSTED, "signer_inactive", "Extension signer is not permitted for new packages")
            try:
                Ed25519PublicKey.from_public_bytes(signer.public_key).verify(b64url_decode(str(signature["signature"])), canonical_manifest)
            except (InvalidSignature, ValueError) as exc:
                raise PackageVerificationError(ExtensionSignatureStatus.TAMPERED, "signature_invalid", "Extension package signature verification failed") from exc
            declared = {entry.path: entry for entry in manifest.files}
            archive_payloads = set(names) - _META_FILES
            if set(declared) != archive_payloads:
                raise PackageVerificationError(ExtensionSignatureStatus.TAMPERED, "payload_index", "Extension package payload does not match the signed manifest")
            payloads: dict[str, bytes] = {}
            for path, item in declared.items():
                contents = archive.read(path)
                if len(contents) != item.size or hashlib.sha256(contents).hexdigest() != item.sha256:
                    raise PackageVerificationError(ExtensionSignatureStatus.TAMPERED, "payload_digest", "Extension package payload verification failed")
                payloads[path] = contents
            return VerifiedExtensionPackage(
                manifest=manifest,
                package_path=package,
                package_sha256=hashlib.sha256(raw_package).hexdigest(),
                manifest_sha256=hashlib.sha256(canonical_manifest).hexdigest(),
                signer_key_id=signer.key_id,
                verified_at=datetime.now(UTC),
                payload_bytes=payloads,
            )
        finally:
            archive.close()
