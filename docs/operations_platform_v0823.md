# Aurora Relay operations platform — v0.8.23 design record

**Status:** implementation plan accepted for a phased, local-first delivery.

## Scope and sequencing

This work is implemented in the requested operational order: **health dashboard**, credential-vault hardening, extension registry and manager, visual regression, then deterministic documentation generation. Each phase is independently testable and retains the protected Windows release workflow unchanged.

| Phase | Public surface | Compatibility rule |
| --- | --- | --- |
| Health | Authenticated operational snapshot, dedicated Zustand slice, lazy dashboard | `/health` remains an unauthenticated Electron startup probe; dashboard data never exposes credential values |
| Vault | Scoped credential references, lock status, native desktop capability boundary | Existing encrypted connector ciphertext and configuration records remain valid; no secret enters frontend state |
| Extensions | Local manifest registry, reviewed sample plugins, manager UI | Existing GitHub and Revit connectors remain first-class built-ins until explicitly enabled adapter manifests are reviewed |
| Visual regression | Deterministic Chromium/Linux baselines, explicit update command | Existing interaction suite continues to run unchanged |
| Documentation | Checked-in Markdown generated from reviewed source and manifests | Documentation generation has no network access and does not alter runtime state |

## Health snapshot boundary

`GET /health` remains deliberately small, unauthenticated, and limited to the Electron readiness loop. A new authenticated `/api/v1/operations/health` route will return only the current user’s connector and loop data, plus static release-evidence claims already committed to the application. It will derive activity from the audit log and persist only user-dismissed alert identifiers locally in the client. CPU and memory are reported only when the desktop host provides those values; absence is represented as unavailable rather than fabricated.

Health refresh is operator-controlled with a 30-second default **only while the health view is visible**. The fallback is a deterministic local snapshot, so the browser build makes no external requests and remains useful offline.

## Credential-vault boundary

The existing Python `CredentialVault` remains the application’s cryptographic data-plane: connector ciphertext stays encrypted at rest and never crosses the API boundary. The Electron host now provisions the backend’s Fernet key through the reviewed `@github/keytar` native adapter: **Windows Credential Manager**, macOS Keychain, or Linux Secret Service is the preferred per-user store. The native adapter is an explicit permitted build in the Electron workspace and is validated by a desktop vault smoke test before packaging. The renderer receives only a status record through a narrow IPC method; it cannot call the provider or read a key.

If the native provider is unavailable, Electron may use its available encrypted `safeStorage` facility to persist only the Fernet key in the current user’s application data directory. On Linux, the insecure `basic_text` backend is rejected. If neither the native store nor the encrypted fallback is usable, the launcher marks the vault **locked**, omits the key from the backend environment, and the Python vault rejects encryption and decryption. Existing ciphertext is preserved; it is not re-encrypted, deleted, or silently replaced. A legacy file key is migrated only when it is syntactically valid and the new protected store accepts it.

The authenticated operations endpoint returns only vault **state**, provider class, fallback flag, and a non-secret explanatory message. Master-password, import/export, plaintext reveal/copy operations, and arbitrary credential inspection remain intentionally deferred. Development environment keys retain compatibility for tests and controlled local tooling, but production desktop launches prefer OS protection and surface a lock instead of weakening the trust boundary.

## Extension safety policy

The user-requested ability to load npm packages and arbitrary URLs conflicts with Aurora Relay’s local-first fail-closed execution boundary. v0.8.23 therefore implements an offline local-manifest registry and a reviewed sample extension scaffold. It records remote or package locations only as **untrusted discovery metadata**; it does not download, evaluate, or execute them.

Extension manifests are schema-validated with identifiers, type, version, explicit permissions, and local entrypoint. Unsupported or unapproved permissions leave an extension disabled. `network`, filesystem, session mutation, connector mutation, and all arbitrary code execution are denied by default. The extension service cannot access credentials, raw IPC, Electron APIs, or the host filesystem. Any future executable extension must use a Docker-backed worker and a narrow, sender-validated Electron preload bridge, in line with [Electron’s security recommendations](https://www.electronjs.org/docs/latest/tutorial/security).

## Visual and documentation policy

Visual baselines use a single Chromium/Linux project, deterministic local fixture data, a no-animation screenshot stylesheet, and an explicit `test:visual:update` command. Baseline snapshots are reviewed assets committed to source control; platform-specific rendering is not compared across operating systems.

Documentation generation is deterministic and offline. It parses approved TypeScript interfaces, Python route/service docstrings, and local extension manifests into Markdown under `docs/generated/`. Generation must be run explicitly and a freshness check validates the committed output. Documentation publishing, GitHub Pages deployment, and remote community catalog feeds are excluded from this release because they require a separate approval and CI policy.

## Acceptance guardrails

1. No desktop host execution occurs without Docker for code-execution workloads.
2. No credential plaintext, vault key, or environment secret is returned by an API, stored in Zustand, or logged.
3. Existing GitHub and Revit connector APIs stay stable and user-scoped.
4. The scheduler stays disabled by default and its expiry, action, and review-branch guardrails are unchanged.
5. Every new route requires the existing authentication dependency and owner filtering.
6. A successful test matrix must include backend, TypeScript, production build, offline request guard, Electron syntax, interaction, and visual tests.
