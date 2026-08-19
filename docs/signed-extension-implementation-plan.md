# Signed Extension Packages: Backend and Keyring-Rotation Implementation Plan

**Status:** Implementation planning artifact  
**Recorded:** 2026-08-19  
**Author:** Manus AI  
**Prerequisite:** [Signed Extension Package Verification Design](./signed-extension-verification-design.md)

## Delivery objective

This workstream replaces Aurora Relay’s current raw manifest-and-entrypoint runtime discovery with verified local `.aurx` archives. The implementation is complete only when the backend can prove a package is trusted and intact at every security-sensitive transition, the local keyring can rotate and revoke signers without a network dependency, and an invalid package cannot reach Docker or any host-execution path.

The sequence deliberately establishes the verifier and its negative tests before changing the registry. It then wires lifecycle enforcement, persistence, API contracts, and desktop keyring operations. This avoids a partial state in which an archive is parsed or enabled before its trust decision is available.

## Scope and release gates

| Gate | Required outcome | Blocks |
| --- | --- | --- |
| G1 — Cryptographic core | Canonical manifest, strict ZIP reader, Ed25519 verifier, and signed keyring have deterministic positive and negative tests. | Registry migration and package signing. |
| G2 — Lifecycle enforcement | Catalogue, installation, enablement, and pre-execution all accept only `VerifiedExtensionPackage`. | Any extension activation. |
| G3 — State and migration | Existing installation rows migrate to disabled `unsigned`; safe status is persisted and exposed. | Frontend activation controls. |
| G4 — Operator key lifecycle | Key generation, planned rotation, revocation, recovery, and audit actions are protected and status-only in the renderer. | Production package signing. |
| G5 — Package migration | Built-in extension sources produce checked-in signed `.aurx` packages verified by CI. | Release delivery. |
| G6 — Full validation | Backend, migration, API, browser, visual, documentation, offline, and CI gates pass. | Commit, push, checkpoint, or release. |

> **Release invariant:** No ticket may introduce a compatibility switch that allows unsigned legacy manifests or loose entrypoints to load in a production registry.

## Workstream A — Backend verifier and lifecycle tickets

| ID | Ticket | Depends on | Implementation scope | Acceptance criteria |
| --- | --- | --- | --- | --- |
| AR-EXT-001 | Pin canonicalization dependency and create signing module boundary | None | Add `rfc8785` to `requirements.txt`; create `backend/app/services/extensions/signing.py`; define stable error codes, strict JSON parsing with duplicate-key rejection, and typed package/keyring models. | Dependency lock/install succeeds; ordinary JSON serialization is not used for signature bytes; malformed JSON and duplicate keys are rejected with a safe machine-readable code. |
| AR-EXT-002 | Implement defensive `.aurx` archive inspection | AR-EXT-001 | Read ZIP archives without extraction; enforce member allow-list, count/size/compression-ratio limits, UTF-8 policy, no encryption, no duplicate names, no symlinks, and normalized POSIX paths. | Tests cover traversal, duplicate member, symlink, encrypted member, unindexed file, limit breach, malformed encoding, and valid archive cases; no archive member is trusted by path alone. |
| AR-EXT-003 | Implement canonical manifest and payload binding | AR-EXT-001, AR-EXT-002 | Add typed package manifest fields, RFC 8785 signing bytes, detached-envelope parsing, and SHA-256/size verification for every declared payload. | A signature over a manifest with modified permission, entrypoint, digest, or payload fails; an unlisted or missing payload fails; verified payload bytes remain associated with the inspected archive handle. |
| AR-EXT-004 | Implement trusted keyring verification and signer selection | AR-EXT-001 | Load the bootstrap root and local signed keyring; recompute key IDs; enforce key usage, activation bounds, retirement, revocation, generation monotonicity, and atomic keyring reads. | Unknown/revoked/retired-for-new-package signers fail; only an active `package` key verifies a package; unavailable or malformed trust data yields `trust_unavailable` and no fallback. |
| AR-EXT-005 | Produce `VerifiedExtensionPackage` and ephemeral payload staging | AR-EXT-002, AR-EXT-003, AR-EXT-004 | Return immutable verified identity data and payload bytes or a restricted temporary staging path; ensure cleanup and race-safe open/verify/stage flow. | The service cannot request a raw entrypoint path; a post-verification replacement of the source archive does not alter bytes executed by the current request; staging cleanup occurs on success and error. |
| AR-EXT-006 | Migrate the registry from loose files to verified packages | AR-EXT-005 | Change `ExtensionRegistry` to discover only `.aurx` packages in controlled locations; return verified catalogue values and safe status diagnostics; prohibit old raw manifests at runtime. | A legacy `manifests/*.json` file never appears in the usable catalogue; a valid signed package does; an invalid package is omitted from runnable catalogue data and records a non-sensitive status. |
| AR-EXT-007 | Enforce verification throughout extension lifecycle | AR-EXT-006 | Refactor `ExtensionService.catalog`, `install`, `update(enabled=True)`, and `execute` to re-verify; compare current installed identity with persisted digests/signer; block and audit drift. | Tampering after install disables a record during enable/execute; Docker initialization is not called after verification failure; a verified disabled package stays disabled until explicit enablement. |
| AR-EXT-008 | Persist verification evidence and migrate legacy records | AR-EXT-007 | Add fields for signature status, signer key ID, package and manifest digests, verification time, and bounded reason code; create Alembic migration that disables legacy enabled rows and marks them `unsigned`. | Upgrade and downgrade are tested on SQLite; no existing installation becomes trusted automatically; migrated enabled rows are disabled atomically; secret or signature bytes never enter the table. |
| AR-EXT-009 | Add safe authenticated API contracts and audit events | AR-EXT-007, AR-EXT-008 | Add signature-status enum/response fields; return typed security-conflict responses; audit verification and state changes without exposing parser or crypto internals. | Owner scoping remains intact; API shows safe status, signer ID, and verification time only; blocked operation responses do not leak raw package paths, stack traces, keys, or signature bytes. |
| AR-EXT-010 | Update deterministic documentation generation | AR-EXT-006, AR-EXT-009 | Make `scripts/generate_docs.py` enumerate verified packages only and publish signer/status metadata without secrets. | Generated docs omit legacy loose manifests; `--check` fails if package metadata or generated reference is stale; output contains no private material. |

## Workstream B — Keyring rotation and desktop operator tickets

| ID | Ticket | Depends on | Implementation scope | Acceptance criteria |
| --- | --- | --- | --- | --- |
| AR-KEY-001 | Add isolated extension-signing vault records | AR-EXT-001 | Extend `desktop/electron/vault.js` with a distinct service/account namespace for extension signing keys; retain native-keychain-first and encrypted fallback policy; preserve vault lock behavior. | Extension signing material cannot be read through connector-vault APIs; renderer receives only `{state, backend, fallback, activeKeyId}`; Linux `basic_text` remains a fail-closed condition. |
| AR-KEY-002 | Provision bootstrap root and signed local keyring | AR-EXT-004, AR-KEY-001 | Package a non-secret bootstrap root; create owner-only application-data trust directory; verify and atomically apply the first signed keyring at desktop/backend startup. | First run yields a valid keyring or locked trust state; a partially written keyring is never accepted; backend receives public trust configuration only and no private seed. |
| AR-KEY-003 | Build operator signing and verification CLI | AR-EXT-003, AR-EXT-004, AR-KEY-001 | Implement `scripts/sign_extension.py` subcommands: `init-key`, `show-public-key`, `sign`, `verify`, `build-keyring`, `rotate-key`, and `revoke-key`. Require explicit local paths and confirmations for destructive/key-state actions. | CLI signs a fixture package that backend verification accepts; it refuses unprotected private-key export by default; output redacts key seed; invalid updates leave the current keyring unchanged. |
| AR-KEY-004 | Implement planned key rotation | AR-KEY-002, AR-KEY-003 | Generate new active signing key, store it securely, create a generation-incremented keyring signed by an incumbent `keyring` key, then retire the prior signing key after package migration. | Rotation requires authenticated operator confirmation and creates an audit event; old packages continue verifying while prior key is trusted; retired key cannot sign newly accepted packages after its cutoff. |
| AR-KEY-005 | Implement revocation and extension containment | AR-KEY-004, AR-EXT-007 | Create a signed revocation update path; immediately reject the revoked signer on all verifier calls; disable impacted installations and capture safe audit evidence. | A revoked package cannot catalogue, enable, or execute; existing enabled installations become `blocked` at next verification; no automatic re-enable occurs after replacement. |
| AR-KEY-006 | Define emergency bootstrap-root recovery | AR-KEY-002 | Implement a recovery package/resource path that is accepted only through the existing protected desktop-installer update; add operational runbook and test fixtures. | A compromised signer cannot self-authorize a new bootstrap root; emergency root change requires signed application delivery; recovery test proves the old root cannot authorize the replacement alone. |
| AR-KEY-007 | Expose status-only operator controls | AR-KEY-002, AR-KEY-004, AR-KEY-005 | Add narrow Electron main-process handlers, preload types, backend/admin endpoint as needed, and audited UI commands for keyring status, planned rotation, and revocation confirmation. | No generic filesystem/key API is exposed; controls require owner authentication and explicit confirmation; UI never displays private material, raw keyring bytes, or package signature bytes. |

## Workstream C — Package migration, end-to-end validation, and rollout tickets

| ID | Ticket | Depends on | Implementation scope | Acceptance criteria |
| --- | --- | --- | --- | --- |
| AR-REL-001 | Build and sign reviewed built-in packages | AR-EXT-006, AR-KEY-003 | Convert sandbox echo, GitHub adapter, and Revit adapter into signed `.aurx` archives; move loose source files out of runtime registry. | Every checked-in runtime package verifies under the packaged public keyring; no private key is committed; package output is reproducible. |
| AR-REL-002 | Add backend and migration security matrix | AR-EXT-009, AR-KEY-006, AR-REL-001 | Expand `backend/tests/test_extensions.py` and migration tests for valid, unsigned, tampered, unknown, revoked, malformed, trust-unavailable, post-install modification, and Docker-not-called paths. | Focused suite covers every status and transition; complete backend suite passes. |
| AR-REL-003 | Add frontend and Electron contract coverage | AR-KEY-007, AR-EXT-009 | Add trust-state types, status badges, disabled controls, operator keyring state, interaction tests, and visual baseline update. | Verified and blocked states are visually distinct; untrusted controls cannot trigger a lifecycle call; renderer receives no sensitive state. |
| AR-REL-004 | Add CI and release safeguards | AR-REL-001, AR-REL-002, AR-REL-003, AR-EXT-010 | Add package verification before documentation freshness; ensure PR CI verifies public artifacts only; add protected-release signing key requirement and secret scan rule. | CI fails on invalid package/keyring, stale docs, or private-key material; protected release is the only signing context. |
| AR-REL-005 | Stage migration and operator rehearsal | AR-REL-004 | Run a migration rehearsal from current local SQLite state; test planned rotation, revocation containment, and emergency recovery with fixtures; document operator commands and rollback. | Existing records become disabled `unsigned`; verified replacements require explicit install/enable; rehearsals produce audit evidence and no host execution. |
| AR-REL-006 | Complete release validation and evidence | AR-REL-005 | Run all backend, frontend, Electron, offline, visual, docs, CI-config, and package-verification gates; save evidence; then commit/push/checkpoint. | All gates are green, limitations are recorded, no tag or release is created without explicit approval, and the immutable release history is preserved. |

## Dependency-driven delivery sequence

The recommended execution order is **AR-EXT-001 through AR-EXT-005**, then **AR-EXT-006 and AR-EXT-007**. Once the runtime verifier is enforceable, complete **AR-EXT-008 through AR-EXT-010** while Workstream B begins with **AR-KEY-001 through AR-KEY-003**. Planned rotation and revocation are then delivered by **AR-KEY-004 and AR-KEY-005**, with emergency recovery handled independently by **AR-KEY-006**. Only after those boundaries are validated should Aurora Relay create production packages under **AR-REL-001** and proceed through the release gates.

```text
Cryptographic core ──> Verified package boundary ──> Registry + lifecycle enforcement
        │                         │                           │
        └──> Trust keyring ───────┴──> Vault + operator tools ┴──> Signed built-ins
                                                                  │
                            Migration + API + UI <───────────────┤
                                                                  ▼
                                                      CI + rehearsal + evidence
```

## Definition of done

The workstream is done only when every runtime package is a verified `.aurx` archive, the registry has no loose-file execution route, all lifecycle transitions re-verify current bytes, the keyring can rotate and revoke offline under an authenticated operator boundary, and the renderer never receives private or raw trust material. The implementation must preserve the existing Docker-only execution policy, local-only operating model, protected release process, and user-scoped API authorization.

The next application workstream—authenticated health history retention—starts only after this definition of done and its validation evidence are complete.
