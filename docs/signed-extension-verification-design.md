# Signed Extension Package Verification Design

**Status:** Approved implementation approach — no runtime changes made by this design record  
**Recorded:** 2026-08-18  
**Scope:** Aurora Relay local extension registry, lifecycle service, desktop trust boundary, authenticated extension UI, tests, and CI checks

## Executive decision

Aurora Relay will replace its unsigned manifest-and-entrypoint discovery with a **fail-closed, local `.aurx` package format**. A package is accepted only when an explicitly trusted, non-revoked Ed25519 public key verifies a detached signature over a canonical manifest and that manifest binds every executable payload file by SHA-256 digest. No unsigned package, tampered payload, unknown key, revoked key, malformed archive, or unavailable trust bundle can be registered, enabled, loaded, or passed into the Docker sandbox.

This is intentionally an **offline trust model**. Aurora Relay will not fetch packages, keys, revocation records, or telemetry. It protects the intended boundary—unreviewed local extension content cannot become active merely by being copied into an extension directory. It does not claim to protect against a local attacker who can already alter the signed desktop application, its protected installation, or the current user’s trusted local state. Existing Authenticode release signing, OS account separation, and restrictive file permissions remain relevant complementary controls.

## Security objectives and boundaries

| Objective | Design response | Explicit non-goal |
| --- | --- | --- |
| Authenticate publisher | Verify a detached Ed25519 signature with a pinned local public key. | Public-key infrastructure, remote certificate discovery, or commercial code-signing certificates. |
| Preserve manifest integrity | Canonicalize the validated manifest under RFC 8785 before signing and verification. | Treating whitespace-preserving raw JSON as a security primitive. |
| Preserve executable integrity | Require a normalized path, SHA-256 digest, and size for every package payload. | Trusting a manifest signature without binding entrypoint bytes. |
| Prevent untrusted execution | Verify at discovery, installation, enablement, and immediately before staging code for Docker. | Host execution, shelling out, or a permissive development fallback. |
| Support offline key lifecycle | Carry a signed local keyring and a deliberate operator rotation/revocation workflow. | Silent remote key refresh or automatic extension updates. |
| Keep secrets out of the renderer | Keep signing private keys in the operator-controlled desktop vault only; expose status and public signer identity only. | Renderer access to seed material, vault records, or generic key-management IPC. |

> **Security invariant:** A successful signature check is necessary but not sufficient for execution. Aurora Relay also requires a supported extension kind, allow-listed permissions, explicit user installation, explicit enablement, and an available Docker sandbox.

## Cryptographic profile

The verifier will use `cryptography>=42.0`, already present in `requirements.txt`, with `Ed25519PublicKey.verify`. The library provides Ed25519 key generation, raw key serialization, 64-byte signatures, and an `InvalidSignature` exception on verification failure.[1] The signing payload is the UTF-8 bytes produced by the `rfc8785` package’s `dumps` implementation, pinned in `requirements.txt`; the package implements the JSON Canonicalization Scheme and rejects values outside its canonicalization domain.[2] RFC 8785 exists specifically so hashing and signatures operate on an invariant JSON representation even when the ordinary JSON wire representation differs.[3]

| Element | Decision |
| --- | --- |
| Algorithm | Ed25519 / EdDSA; no algorithm negotiation in version 1. |
| Public-key encoding | Raw 32-byte public key, base64url without padding. |
| Signature encoding | Raw 64-byte signature, base64url without padding, inside a small JSON envelope. |
| Key identifier | `ed25519:sha256:<base64url(SHA-256(raw-public-key))>`; recomputed and compared, never trusted solely from package text. |
| Manifest canonicalization | Strict JSON parse with duplicate-key rejection, Pydantic schema validation, then RFC 8785 canonicalization. |
| Payload digest | Lowercase hexadecimal SHA-256 of exact uncompressed bytes. |
| Signature scope | Entire canonical manifest, including package format, extension metadata, permissions, entrypoint reference, and payload index. |

The release implementation must avoid Python’s ordinary `json.dumps(sort_keys=True)` as a substitute for RFC 8785. Its number and string behavior is not the JCS interoperability contract. Manifest version 1 will consequently prohibit floating-point fields and keep all sizes as bounded integers.

## `.aurx` package format

The `.aurx` extension is a ZIP container. The extension is only an operator-facing convention; the verifier always validates archive contents rather than relying on the filename.

```text
aurora.sandbox-echo-1.0.0.aurx
├── manifest.json
├── manifest.json.sig
└── payload/
    └── sandbox-echo.js
```

`manifest.json` will remain the application’s typed `ExtensionManifest` data and acquire only the minimum package-binding fields shown below. It does **not** embed its own signature, because the detached signature is a separate artifact.

```json
{
  "package_format": "aurora-extension/v1",
  "id": "aurora.sandbox-echo",
  "display_name": "Sandbox echo",
  "version": "1.0.0",
  "description": "A reviewed Docker-only JavaScript echo tool.",
  "kind": "sandboxed_tool",
  "permissions": ["sandbox.execute"],
  "entrypoint": "payload/sandbox-echo.js",
  "files": [
    {
      "path": "payload/sandbox-echo.js",
      "sha256": "<64 lowercase hexadecimal characters>",
      "size": 31
    }
  ]
}
```

`manifest.json.sig` is a JSON envelope with exactly `format`, `key_id`, and `signature` fields. Its versioned `format` value is `aurora-ed25519/v1`; the `signature` is over the RFC 8785 bytes of `manifest.json`. The verifier selects a trusted public key by recomputed `key_id`, checks its validity window and state, then verifies the signature. The key identifier is metadata for key selection, not a substitute for cryptographic verification.

The archive policy will reject a missing or duplicate manifest/signature, encrypted ZIP entries, symlinks, duplicate names, absolute or backslash paths, `.`/`..` segments, NUL bytes, unindexed content, unlisted payload files, invalid UTF-8, unsupported compression methods, files exceeding configured per-file or total limits, and excessive compression ratios. `manifest.json` and `manifest.json.sig` have dedicated tight size caps. The verifier will calculate each file hash while reading the same archive handle it validates; it will never validate one path and later execute bytes re-opened from a mutable path.

Connector-adapter packages contain `manifest.json` and `manifest.json.sig` with an empty `files` array. Sandboxed tools include a payload entrypoint. Dashboard panels remain metadata-only until a separate, hardened renderer-extension execution design is approved; a signed package does not authorize webview or Node integration.

## Trust-root and key lifecycle model

Aurora Relay separates **publisher private keys**, **runtime trusted public keys**, and **the desktop application’s existing release-signing identity**. They are different controls and must never be conflated.

| Material | Residence | Access model | Runtime role |
| --- | --- | --- | --- |
| Publisher Ed25519 private seed | Electron main-process vault account named `Aurora Relay Extension Signing Key/<key-id>` on a dedicated operator signing machine. | Explicit local signing command only; never passed to the backend or renderer. | Signs reviewed packages and keyring updates. |
| Trusted public-key bundle | Per-install application-data trust directory, with owner-only permissions and an atomic write protocol. | Backend verifier reads a public bundle; Electron exposes only a summary status. | Selects permitted package signers and their state. |
| Bootstrap root public key | Packaged resource protected by the existing signed Aurora Relay installer. | Read-only application resource. | Verifies the first local keyring and recovery keyring updates. |
| Desktop release-signing certificate | Protected release environment / installer flow. | Existing release process. | Protects delivery of the bootstrap root and emergency recovery build. |

The keyring is a small signed local document containing `schema`, `generation`, `issued_at`, `keys`, and `revocations`. Each trusted key records `key_id`, raw public key, allowed usage (`package` and/or `keyring`), state (`active`, `retired`, or `revoked`), and optional validity bounds. The entire keyring is signed by an already trusted key with `keyring` usage, then applied with `write-temp → fsync → atomic rename`. Runtime verification fails closed if no valid bootstrap key, no valid signed keyring, or no active allowed signer is available.

A planned rotation generates a new Ed25519 key locally, stores the private seed in the native vault, and creates a keyring update signed by the incumbent key. The operator applies that update through an authenticated desktop action with a confirmation boundary and audit event. A retiring signer may continue verifying previously published packages, but must not sign new packages after its `retired_at` timestamp. A revoked signer is rejected immediately at the next catalogue, lifecycle, or execution verification; affected extensions are disabled and marked blocked until re-signed by an active trusted key.

Emergency recovery cannot safely rely on a potentially compromised key to authorize its replacement. It therefore requires an Aurora Relay desktop update delivered through the existing protected, signed installer workflow. The update pins a replacement bootstrap root and new signed keyring, disables the compromised key identifiers, and requires packages to be re-signed. There is no automatic network recovery path.

## Verification flow and lifecycle enforcement

The current registry discovers `backend/extensions/manifests/*.json` and the service separately reads `entries/`. This is inadequate once archive content must be bound to the manifest. The implementation will replace those locations with `backend/extensions/packages/*.aurx` for shipped reviewed packages and an owner-controlled per-install package directory for imported reviewed archives. Raw manifest directories become migration-only and are never executable after the signed-package release.

| Boundary | Required operation | Failure result |
| --- | --- | --- |
| Catalogue discovery | Parse ZIP defensively; validate manifest; verify signer state and detached signature; validate every declared payload digest. | Omit untrusted manifest metadata from the usable catalogue; retain only generic package filename and safe verification state for operator diagnostics. |
| Install | Re-verify the current package and persist immutable identity data. | Reject request; write a security audit event without exposing parser internals. |
| Enable/load | Re-verify and compare extension ID, version, package SHA-256, manifest SHA-256, and signer key ID with the installed record. | Disable record, set lifecycle status `blocked`, and return a safe verification reason. |
| Pre-execution | Re-verify from a single open archive; stage verified entrypoint bytes into an ephemeral restricted directory or pass verified bytes directly to the sandbox. | Do not initialize or invoke a Docker container for extension code. |
| Docker execution | Apply existing allow-listed language, no-network, non-root, bounded-time/output sandbox profile. | Preserve the current no-host-fallback rule. |

The verifier will return a `VerifiedExtensionPackage` value containing the **validated immutable manifest**, `package_sha256`, `manifest_sha256`, `signer_key_id`, verification timestamp, and verified payload bytes or a narrowly scoped staged path. All downstream functions must accept this value instead of accepting an unverified `ExtensionManifest` and resolving a live filesystem path. This removes the present time-of-check/time-of-use gap between registry discovery and `entrypoint_path()` execution.

## Code-level implementation map

| Area | Planned change |
| --- | --- |
| `backend/app/services/extensions/signing.py` | Add strict archive reader, canonical-manifest serializer, trusted-key/keyring loader, Ed25519 verifier, status enum, error codes, verified-package value, and atomic staging helpers. |
| `backend/app/services/extensions/registry.py` | Discover only `.aurx` files; return verified catalogue items; prohibit raw manifests and raw entrypoint resolution for runtime use. |
| `backend/app/services/extensions/service.py` | Enforce verification in `catalog`, `install`, `update(enabled=True)`, and `execute`; turn any re-verification failure into a disabled, auditable `blocked` state. |
| `backend/app/api/models.py` | Add `ExtensionSignatureStatus` such as `verified`, `unsigned`, `tampered`, `untrusted`, `revoked`, `invalid`, and `trust_unavailable`; include safe signer key ID and verification timestamp in responses. |
| `backend/app/database/models.py` | Extend `ExtensionInstallation` with `signature_status`, `signer_key_id`, `package_sha256`, `manifest_sha256`, `verified_at`, and a bounded verification-error code. |
| Alembic migration | Add non-null defaults that classify existing installations as `unsigned`; disable legacy enabled records in the same transaction. |
| `backend/app/api/routes/extensions.py` | Preserve authenticated owner scope and return a typed 409-style blocked/security response for verification failures rather than raw parsing or cryptography errors. |
| `desktop/electron/vault.js` and `main.js` | Add a separately named extension-signing vault account and trust-bundle status. The preload surface gets status only; it receives no private key, package bytes, or generic trust-edit capability. |
| `scripts/sign_extension.py` | Provide `init-key`, `show-public-key`, `sign`, `verify`, `rotate-key`, and `build-keyring` subcommands. Private-key output is prohibited unless an operator explicitly requests an encrypted backup. |
| `frontend` extension types/store/view/commands | Show a trust badge distinct from lifecycle state; disable install/enable/run controls unless the status is `verified`; expose a generic safe explanation and signer fingerprint, never raw package content or key material. |
| Documentation generator and CI | Generate package and signer metadata from verified package manifests only, and fail CI if archive verification or deterministic reference generation fails. |

## Persistence, API, and user experience

The installation row records what was actually verified—not an assertion copied from an archive. It persists `signature_status`, `signer_key_id`, package and manifest digests, `verified_at`, and a machine-safe reason code. Persisted state does not replace current verification: every security-sensitive transition evaluates the current archive again.

The authenticated API returns a concise verification status, signer key identifier, verification time, and non-sensitive recommendation. It will not return signature bytes, raw trust data, parser stack traces, decrypted vault data, or detailed differences useful to a malicious package author. The Aurora Relay dark editorial extension UI will render **Trust** and **Lifecycle** separately: for example, `Verified / Disabled` is an expected state, while `Tampered / Blocked` is a security condition. Only `Verified` packages can offer installation, enablement, or execution actions.

## Migration of reviewed built-ins

The three current reviewed entries—sandbox echo, GitHub connector adapter, and Revit connector adapter—will be rebuilt as `.aurx` archives using the new tool. The private signer is generated in the local secure operator vault and is not committed. The associated public root/keyring, signed package archives, and verification metadata are committed as reviewed non-secret artifacts. The legacy JSON files and loose executable entrypoints may remain as source inputs under a clearly non-runtime `extension-sources/` path, but the runtime registry will never read them.

Existing user installation records are conservatively migrated to `unsigned` and disabled. On the next catalogue refresh, the UI can identify a matching verified replacement package; the user must reinstall and explicitly re-enable it. This intentionally avoids granting trust to a historical manifest that was never signed. There is no silent legacy compatibility mode.

## Test, CI, and operational gates

| Layer | Required coverage |
| --- | --- |
| Unit | Correct Ed25519 verification, base64/key-ID validation, RFC 8785 canonicalization failures, wrong key, revoked key, retired-key policy, malformed signature envelope, and trust-store unavailability. |
| Archive security | Missing/duplicate members, duplicate JSON keys, path traversal, symlink, encrypted member, unlisted file, missing indexed file, digest mismatch, ZIP size/ratio limits, and malformed UTF-8. |
| Service | Installation, enablement, and execution each re-verify; a package changed after installation becomes `blocked`; Docker is never entered for an invalid package; enabled legacy records become disabled. |
| API and persistence | Owner-scoped responses expose safe status only; migration writes expected fields; audit events capture status and non-secret key identifier. |
| Frontend / Playwright | Verified package enables allowed controls; unsigned, tampered, untrusted, revoked, and trust-unavailable packages show distinct safe trust badges and no active controls. |
| CI | Run package verification against every checked-in `.aurx`, ensure no private key or seed appears in Git history/package artifacts, run generated-doc freshness, backend suite, Playwright interaction suite, visual baseline, type check, build, and offline request guard. |
| Release | Protected release workflow may sign packages only with a protected signing key; ordinary pull-request validation verifies committed public artifacts but cannot access signing material. |

The current backend CI job already runs dependency installation, Python compilation, deterministic documentation freshness, and the backend test suite. The package verifier will be inserted before documentation generation, so `scripts/generate_docs.py --check` consumes only verified manifest metadata. The current frontend job will absorb trust-badge interaction assertions and an intentional visual baseline update, while the existing filesystem scan continues to reject accidental private-key material. The release workflow alone may receive a protected signing key; ordinary pull-request validation verifies committed packages only.

Package signing will be deterministic: sorted members, fixed ZIP metadata, canonical manifest, and deterministic Ed25519 signatures. CI verifies package content and records package SHA-256 values as release evidence. It must not auto-rotate keys, auto-import trust data, or automatically activate a new extension.

## Implementation sequence

The implementation will proceed as a vertical security slice. First, add the signing dependency, verifier, trust/keyring reader, test-fixture package builder, and negative archive tests. Second, move the registry and lifecycle service to `VerifiedExtensionPackage`, add the persistence migration, and repackage the three reviewed extensions. Third, wire safe API/UI trust status and desktop status-only key management. Finally, add CI verification, deterministic documentation, complete regression/visual validation, and commit/push the implementation only after the complete matrix is green.

Authenticated health-history retention is intentionally deferred until this signed-package slice has passed its full validation gate. Manual renderer bundle splitting remains explicitly out of scope.

## References

[1] [PyCA cryptography — Ed25519 signing](https://cryptography.io/en/latest/hazmat/primitives/asymmetric/ed25519/)  
[2] [Trail of Bits `rfc8785` Python API documentation](https://trailofbits.github.io/rfc8785.py/)  
[3] [RFC 8785 — JSON Canonicalization Scheme](https://datatracker.ietf.org/doc/html/rfc8785)
