#!/usr/bin/env python3
"""Offline Aurora Relay extension-package signing utility.

Private keys are explicit input files and are never written to the repository,
database, renderer, or package archive. Run this only from a secured publisher
workstation; CI verifies already-built packages but does not sign them.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sys
import zipfile
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.services.extensions.signing import b64url_encode, canonical_json, key_id_from_public_key  # noqa: E402


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_private(path: Path) -> Ed25519PrivateKey:
    value = serialization.load_pem_private_key(path.read_bytes(), password=None)
    if not isinstance(value, Ed25519PrivateKey):
        raise ValueError("Signing key must be an Ed25519 private key")
    return value


def _public_record(private: Ed25519PrivateKey) -> dict[str, str]:
    raw = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return {"key_id": key_id_from_public_key(raw), "public_key": b64url_encode(raw)}


def generate_key(args: argparse.Namespace) -> None:
    private = Ed25519PrivateKey.generate()
    args.private_out.parent.mkdir(parents=True, exist_ok=True)
    args.private_out.write_bytes(
        private.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    )
    _write_json(args.public_out, _public_record(private))
    print(f"Created private key at {args.private_out}; store it outside the Aurora Relay repository.")
    print(f"Created public identity at {args.public_out}.")


def sign_keyring(args: argparse.Namespace) -> None:
    private = _load_private(args.bootstrap_private)
    keyring = _json(args.keyring)
    keyring.pop("signature", None)
    if keyring.get("schema") != "aurora-keyring/v1":
        raise ValueError("Keyring schema must be aurora-keyring/v1")
    public = _public_record(private)
    keyring["signature"] = {
        "format": "aurora-ed25519/v1",
        "key_id": public["key_id"],
        "signature": b64url_encode(private.sign(canonical_json(keyring))),
    }
    _write_json(args.output, keyring)


def build_package(args: argparse.Namespace) -> None:
    private = _load_private(args.signing_private)
    source_manifest = _json(args.manifest)
    source_manifest["package_format"] = "aurora-extension/v1"
    payloads: list[tuple[str, Path]] = []
    if source_manifest.get("kind") == "sandboxed_tool":
        entrypoint = str(source_manifest.get("entrypoint", ""))
        if not entrypoint:
            raise ValueError("Sandboxed package manifest requires an entrypoint")
        path = (args.payload_root / entrypoint).resolve()
        if not path.is_file() or args.payload_root.resolve() not in path.parents:
            raise ValueError("Entrypoint must be a file below payload-root")
        archive_path = f"payload/{entrypoint}"
        source_manifest["entrypoint"] = archive_path
        payloads.append((archive_path, path))
    source_manifest["files"] = [
        {"path": archive_path, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "size": path.stat().st_size}
        for archive_path, path in payloads
    ]
    signature = {
        "format": "aurora-ed25519/v1",
        "key_id": _public_record(private)["key_id"],
        "signature": b64url_encode(private.sign(canonical_json(source_manifest))),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.output, "w", compression=zipfile.ZIP_DEFLATED, strict_timestamps=True) as archive:
        archive.writestr("manifest.json", canonical_json(source_manifest), compress_type=zipfile.ZIP_DEFLATED)
        archive.writestr("manifest.json.sig", canonical_json(signature), compress_type=zipfile.ZIP_DEFLATED)
        for archive_path, path in payloads:
            archive.writestr(archive_path, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED)
    print(f"Created verified package candidate: {args.output}")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Offline Aurora Relay signed-extension tooling")
    sub = result.add_subparsers(dest="command", required=True)
    generate = sub.add_parser("generate-key", help="Generate an Ed25519 publisher or bootstrap key pair")
    generate.add_argument("--private-out", type=Path, required=True)
    generate.add_argument("--public-out", type=Path, required=True)
    generate.set_defaults(func=generate_key)
    keyring = sub.add_parser("sign-keyring", help="Sign a keyring using the pinned bootstrap private key")
    keyring.add_argument("--bootstrap-private", type=Path, required=True)
    keyring.add_argument("--keyring", type=Path, required=True)
    keyring.add_argument("--output", type=Path, required=True)
    keyring.set_defaults(func=sign_keyring)
    package = sub.add_parser("build-package", help="Build and sign one local .aurx archive")
    package.add_argument("--manifest", type=Path, required=True)
    package.add_argument("--payload-root", type=Path, required=True)
    package.add_argument("--signing-private", type=Path, required=True)
    package.add_argument("--output", type=Path, required=True)
    package.set_defaults(func=build_package)
    return result


if __name__ == "__main__":
    args = parser().parse_args()
    args.func(args)
