# Signed Extension Packages: Dependency Graph, Critical Path, and Security Operations Guide

**Status:** Delivery planning and operations reference  
**Recorded:** 2026-08-19  
**Author:** Manus AI  
**Source plan:** [Signed Extension Packages: Backend and Keyring-Rotation Implementation Plan](./signed-extension-implementation-plan.md)

## How to read the dependency graph

The 23 tickets form a directed acyclic graph rather than a single serial backlog. Each arrow means that the downstream ticket cannot be accepted until the upstream ticket’s acceptance criteria are met. The graph has three streams: the backend verifier and lifecycle stream (`AR-EXT-*`), the local trust/keyring stream (`AR-KEY-*`), and the release-evidence stream (`AR-REL-*`). The release stream joins the first two streams only after verified runtime behavior and safe local key operations exist.

The critical-path analysis below uses a **unit-duration, dependency-only assumption**. It identifies tickets that have zero schedule float in the graph if every ticket takes one implementation unit and resourcing is unconstrained. Actual calendar duration will depend on team capacity, desktop-platform test availability, migration rehearsal complexity, and review time. The right operational rule is therefore to protect the critical **convergence gates**, not to assume there is only one critical linear path.

## Complete dependency graph

| Stream | Ticket | Immediate prerequisites | Primary output | Earliest dependency layer |
| --- | --- | --- | --- | --- |
| Backend | AR-EXT-001 | None | Signing module boundary, canonicalization dependency, typed errors/models | 1 |
| Backend | AR-EXT-002 | AR-EXT-001 | Defensive ZIP archive inspection | 2 |
| Backend | AR-EXT-003 | AR-EXT-001, AR-EXT-002 | Canonical manifest, detached signature, payload binding | 3 |
| Backend | AR-EXT-004 | AR-EXT-001 | Trusted local keyring verification and signer selection | 2 |
| Backend | AR-EXT-005 | AR-EXT-002, AR-EXT-003, AR-EXT-004 | Immutable `VerifiedExtensionPackage` and verified staging | 4 |
| Backend | AR-EXT-006 | AR-EXT-005 | Registry accepts verified `.aurx` packages only | 5 |
| Backend | AR-EXT-007 | AR-EXT-006 | Re-verification at catalogue, install, enable, and execute | 6 |
| Backend | AR-EXT-008 | AR-EXT-007 | Persisted evidence and conservative legacy migration | 7 |
| Backend | AR-EXT-009 | AR-EXT-007, AR-EXT-008 | Safe authenticated API contracts and audit events | 8 |
| Backend | AR-EXT-010 | AR-EXT-006, AR-EXT-009 | Verified-package documentation generation | 9 |
| Keyring | AR-KEY-001 | AR-EXT-001 | Isolated native-vault namespace for extension signing material | 2 |
| Keyring | AR-KEY-002 | AR-EXT-004, AR-KEY-001 | Bootstrap root and signed local keyring provisioning | 3 |
| Keyring | AR-KEY-003 | AR-EXT-003, AR-EXT-004, AR-KEY-001 | Operator signing and verification CLI | 4 |
| Keyring | AR-KEY-004 | AR-KEY-002, AR-KEY-003 | Planned offline key rotation | 5 |
| Keyring | AR-KEY-005 | AR-KEY-004, AR-EXT-007 | Revocation and impacted-extension containment | 7 |
| Keyring | AR-KEY-006 | AR-KEY-002 | Emergency bootstrap-root recovery | 4 |
| Keyring | AR-KEY-007 | AR-KEY-002, AR-KEY-004, AR-KEY-005 | Status-only operator controls | 8 |
| Release | AR-REL-001 | AR-EXT-006, AR-KEY-003 | Signed built-in `.aurx` packages | 6 |
| Release | AR-REL-002 | AR-EXT-009, AR-KEY-006, AR-REL-001 | Backend and migration security test matrix | 9 |
| Release | AR-REL-003 | AR-KEY-007, AR-EXT-009 | Frontend/Electron security contract coverage | 9 |
| Release | AR-REL-004 | AR-REL-001, AR-REL-002, AR-REL-003, AR-EXT-010 | CI and protected-release safeguards | 10 |
| Release | AR-REL-005 | AR-REL-004 | Migration and operator rehearsal | 11 |
| Release | AR-REL-006 | AR-REL-005 | Complete validation evidence; commit/push/checkpoint readiness | 12 |

### Graph at a glance

```text
AR-EXT-001
 ├──> AR-EXT-002 ──> AR-EXT-003 ───────────┐
 │             │              │             ├──> AR-EXT-005 ─> AR-EXT-006 ─> AR-EXT-007 ─> AR-EXT-008 ─> AR-EXT-009 ─> AR-EXT-010
 │             │              │             │                                                   │                    │
 │             └──────────────┼─────────────┘                                                   │                    └──────────────────────┐
 ├──> AR-EXT-004 ─────────────┘                                                                 │                                           │
 │       │                                                                                       │                                           │
 │       ├──> AR-KEY-002 ─> AR-KEY-006 ─────────────────────────────────────────────────────────┼──> AR-REL-002                          │
 │       │             │                                                                         │                                           │
 └──> AR-KEY-001 ──────┼──> AR-KEY-003 ─> AR-REL-001 ───────────────────────────────────────────┼──> AR-REL-002                          │
                       │       │                                                                  │                                           │
                       │       └──> AR-KEY-004 ─> AR-KEY-005 ─> AR-KEY-007 ────────────────────────┴──> AR-REL-003                          │
                       │                              ▲                                                                                       │
                       └──────────────────────────────┘                                                                                       │

AR-REL-001 + AR-REL-002 + AR-REL-003 + AR-EXT-010 ─> AR-REL-004 ─> AR-REL-005 ─> AR-REL-006
```

## Critical path and parallel work

The dominant backend spine is **AR-EXT-001 → AR-EXT-002 → AR-EXT-003 → AR-EXT-005 → AR-EXT-006 → AR-EXT-007 → AR-EXT-008 → AR-EXT-009**. It creates the verified-package boundary, removes loose runtime files, forces lifecycle re-verification, then makes safe state/API evidence available. This spine is a release prerequisite because it feeds both the documentation gate (`AR-EXT-010`) and the backend/migration test gate (`AR-REL-002`).

At the final convergence, three equal-depth dependency lanes must all be ready before CI/release safeguards can begin: **AR-EXT-010**, **AR-REL-002**, and **AR-REL-003**. In dependency-only terms, this means there are multiple critical paths into `AR-REL-004`, rather than one exclusive path. The release tail is unambiguous: **AR-REL-004 → AR-REL-005 → AR-REL-006**. Delaying any one of those tickets delays all evidence, checkpoint readiness, and any later release decision.

| Critical convergence | Why it has no practical float | Delivery management implication |
| --- | --- | --- |
| AR-EXT-005 | It waits for archive safety, signature/payload binding, and keyring verification. | Build and review AR-EXT-002, AR-EXT-003, and AR-EXT-004 as one security design slice. |
| AR-EXT-009 | It requires runtime enforcement and persistent migration state. | Do not start UI activation or end-to-end security contracts on provisional status fields. |
| AR-KEY-005 | Revocation needs both a trustworthy planned-rotation basis and lifecycle containment. | Treat key compromise as an application-state problem, not merely a keyring edit. |
| AR-KEY-007 | Operator controls depend on current trust state, rotation, and revocation. | Keep the renderer integration late and status-only; avoid creating an early generic key-management channel. |
| AR-REL-004 | It joins signed packages, backend tests, frontend/Electron contracts, and verified docs. | Schedule a convergence review before changing CI/release policy. |
| AR-REL-005 and AR-REL-006 | Rehearsal is evidence, not a substitute for it; validation follows rehearsal. | Reserve time for clean fixtures, audit-evidence capture, and issue remediation before checkpoint. |

The most useful parallelization begins after `AR-EXT-001`. One team can take archive/manifest verification (`AR-EXT-002` and `AR-EXT-003`), a second can take keyring verification and vault isolation (`AR-EXT-004` and `AR-KEY-001`), and a third can prepare migration fixture data and package-source structure without changing runtime behavior. After `AR-EXT-006`, the package-build path (`AR-REL-001`) and lifecycle/persistence path (`AR-EXT-007` through `AR-EXT-010`) can progress in parallel. The implementation must still retain the G1–G6 gate order; parallel work does not authorize early activation.

## Fail-closed state handling

Aurora Relay must represent **trust state** separately from **lifecycle state**. Trust answers whether the current archive and signer are acceptable. Lifecycle answers whether an owner has installed/enabled the extension and whether the runtime can operate. A verified package may correctly be `Verified / Disabled`; a package with broken integrity must become `Tampered / Blocked` regardless of a prior enabled flag.

| Signature status | Detection point | Immediate action | Persisted safe evidence | Operator remediation |
| --- | --- | --- | --- | --- |
| `verified` | Valid trusted key, signature, archive policy, and payload digest checks | Catalogue/install/enable/execute may proceed to the next policy gate. | Signer ID, package/manifest digests, verification time. | Explicit install or enable remains required. |
| `unsigned` | Missing detached signature or a legacy loose record | Reject package; migrate existing record as disabled. | `unsigned` reason code and legacy migration marker. | Rebuild/re-sign as `.aurx`, then explicitly reinstall/enable. |
| `invalid` | Malformed manifest/signature envelope, duplicate JSON key, unsafe archive member, or validation-limit violation | Stop processing before extraction/staging. | Bounded invalidity reason code; no raw parser detail. | Rebuild package under the approved format. |
| `tampered` | Signature mismatch, hash/size mismatch, or installed identity drift | Disable installation, set lifecycle to `blocked`, audit event, and prevent Docker initialization. | Current expected/observed identity class, safe reason, time. | Discard package; obtain and verify a newly signed replacement. |
| `untrusted` | Unknown key ID, key not authorized for package use, or key outside valid activation policy | Reject before package activation. | Key ID and non-sensitive trust reason. | Apply an authorized signed keyring update or sign with an existing active key. |
| `revoked` | Key appears in a valid signed revocation record | Disable any affected installed extension on next verification. | Revoked signer ID, revocation generation, time. | Re-sign package under a different active key; explicit reinstall/enable. |
| `trust_unavailable` | Missing/malformed bootstrap/keyring, failed atomic read, or locked trust storage | Block all package activation paths; no permissive local fallback. | Trust-store state and safe availability code. | Restore a valid local trust bundle or use the protected recovery process. |

The transition guard is deliberately repeated. Catalogue discovery validates a package before it becomes usable metadata. Installation validates current bytes and stores immutable verification evidence. Enablement validates again and compares the package, manifest, and signer identities to the installation record. Execution opens one archive, verifies its content, and stages only those verified bytes into a restricted ephemeral location before the Docker sandbox is initialized. A verification failure at any transition overwrites an enabled lifecycle state with `blocked`; it does not preserve prior execution authority.

The externally visible error must be deliberately narrow. The authenticated UI and API can show a status, a safe key identifier, a verification time, and a concise remediation action. They must not show raw ZIP paths, unbounded parser errors, signature bytes, keyring document bytes, decrypted vault material, or stack traces. Security diagnostics with additional detail belong only in protected local audit evidence.

## Offline keyring rotation workflow

The rotation workflow assumes no key server, certificate discovery endpoint, or remote revocation service. All trust changes happen as local, signed state transitions under owner authentication. Private signing material remains in a separate Electron main-process vault namespace; the backend receives only public trust configuration, and the renderer receives only status.

| Step | Operator action | Required verification | Resulting state |
| --- | --- | --- | --- |
| 0. Preflight | Authenticate as owner and confirm native vault/trust store are ready. | Current bootstrap root and signed keyring validate; incumbent has `keyring` usage; current generation is readable. | Rotation may begin; otherwise `trust_unavailable` blocks it. |
| 1. Generate | Create a new Ed25519 signer locally and store its private seed in the isolated extension-signing vault record. | Compute the key identifier from the raw public key; do not export the seed by default. | Candidate key exists locally; renderer sees only a safe status. |
| 2. Authorize | Build keyring generation `n + 1` that adds the candidate key with explicit allowed usage and validity policy. | Sign the candidate keyring with the incumbent trusted key authorized for `keyring` updates. | Candidate keyring is an authenticated local update, not an arbitrary public-key import. |
| 3. Apply atomically | Write temporary owner-only keyring data, flush it, verify it from the bootstrap chain, then atomically rename into place. | Generation must increase; key IDs recompute; signature/usage/revocation checks pass. | New key is active; an interrupted write leaves the prior valid keyring intact. |
| 4. Re-sign and verify | Sign reviewed package replacements with the new active package signer; verify them through the backend verifier. | New packages validate against the applied keyring and package/payload rules. | New signer is in production-ready use; old signer still validates historical packages. |
| 5. Retire | After migration evidence is complete, set a `retired_at` policy for the predecessor. | Retirement policy preserves verification of historical packages but denies new-package acceptance after cutoff. | Old signer is no longer a path for newly accepted packages. |
| 6. Revoke if necessary | Publish a signed revocation update using a non-compromised authorized key. | Every verifier invocation sees revoked status; impacted installs are re-evaluated. | Existing enabled extensions transition to `blocked`; no automatic re-enable. |

Revocation and emergency recovery are distinct paths. Revocation is appropriate when a currently trusted, non-compromised key can authenticate the updated keyring and mark a signer invalid. Emergency bootstrap-root recovery is required when the signing/keyring authority itself might be compromised. In that case, Aurora Relay does not trust a new root signed by the suspect chain. The new bootstrap root and recovery keyring arrive through the existing protected, signed desktop installer update, disable known compromised key identifiers, and require package re-signing. This distinction prevents a compromised signer from authorizing its own replacement trust root.

## Operational decision points

The go/no-go decision after G1 is whether the verifier can establish trusted identity **without** the legacy registry. The go/no-go decision after G3 is whether all lifecycle operations operate on a verified package value rather than a mutable path. The go/no-go decision after G4 is whether local rotation, revocation, and recovery preserve the rule that private material never enters the renderer. The final go/no-go decision after G6 is whether rehearsal and evidence prove the state model under failure, not merely the happy path.

Health-history retention and renderer bundle splitting remain out of this critical path. They should not be introduced into the signed-extension branch because they would broaden validation scope without strengthening the package trust boundary.
