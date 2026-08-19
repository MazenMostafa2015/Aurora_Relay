# Extensibility and visual-baseline research notes

**Recorded:** 2026-08-18

## Electron extension boundary

Electron’s security guidance treats arbitrary remote code as untrusted and warns against executing it with Node.js integration. Aurora Relay will therefore keep third-party extension loading **local, opt-in, and disabled by default**. The initial extension registry will accept only reviewed local manifests and will not fetch or execute URL or package entry points. Any future isolated renderer for a reviewed extension must retain `nodeIntegration: false`, `contextIsolation: true`, renderer sandboxing, restrictive navigation, and a narrow, sender-validated preload bridge.

The core application will not expose raw Electron, filesystem, credential, connector, session, or IPC APIs to extension code. Permissions will be declarative metadata, require explicit operator approval, and map to a small allow-listed command interface. Docker-backed execution remains the only execution path for code that needs to run; unavailable Docker must fail closed.

Source: [Electron Security](https://www.electronjs.org/docs/latest/tutorial/security).

## Visual-regression baseline policy

Playwright supports stable screenshot comparison through `expect(page).toHaveScreenshot()`. Baselines must be generated and evaluated on the same operating-system and browser environment because fonts and rendering characteristics vary. Aurora Relay will maintain committed Chromium/Linux baselines for deterministic routes, use a project-level screenshot style sheet to suppress animation and volatile content, and require an explicit snapshot-update command for intentional changes. Dynamic runtime data will be modeled with deterministic local fixtures rather than masked after rendering.

The initial threshold will be conservative and expressed as a small maximum changed-pixel count rather than the requested global 0.1% ratio, so genuine editorial-layout changes remain visible to reviewers while font rasterization remains manageable in the repository runner.

Source: [Playwright Visual comparisons](https://playwright.dev/docs/test-snapshots).

## Windows credential-manager boundary

Microsoft documents the Windows Credentials Management API as the supported native mechanism for an application to obtain and manage username/password credential information through the user’s credential store. Aurora Relay will keep that native access in the Electron main process only. The renderer and FastAPI backend will receive only an opaque vault status and short-lived scoped operation result; they will never receive native Credential Manager handles or secrets.

The initial implementation will expose a **capability boundary**, not a direct renderer API: the desktop host may later provide an allow-listed `get`, `set`, `delete`, and `status` bridge for connector records addressed by a stable application service/account tuple. If native host access is unavailable, the existing per-user Fernet-encrypted backend vault remains the fallback. That fallback is explicitly surfaced as software-encrypted local storage rather than being represented as OS-vault protection.

Source: [Microsoft Credentials Management API](https://learn.microsoft.com/en-us/windows/win32/secauthn/credentials-management).

## Native credential-store adapter and encrypted fallback

The maintained `@github/keytar` package documents asynchronous password operations backed by the Windows Credential Vault, macOS Keychain, and Linux Secret Service/libsecret. Aurora Relay can use it **only in the Electron main process** to provision its backend Fernet key; the renderer receives a readiness state and provider label, never key material or connector credentials.[^github-keytar]

Electron `safeStorage` provides an encrypted on-disk fallback for a generated Fernet key. Its asynchronous API is non-blocking and reports temporary availability and rotation conditions. On Windows it uses DPAPI, on macOS Keychain, and on Linux a supported secret store. Aurora Relay must reject Linux `basic_text` storage as unavailable rather than silently treating plaintext-equivalent protection as secure.[^electron-safe-storage]

[^github-keytar]: [@github/keytar — npm package documentation](https://www.npmjs.com/package/@github/keytar)
[^electron-safe-storage]: [Electron — safeStorage API](https://www.electronjs.org/docs/latest/api/safe-storage)

## Signed extension package primitives

Aurora Relay will use **Ed25519** with the maintained Python `cryptography` implementation for local extension-package signatures. The library exposes key generation, signature creation, public-key verification, raw-key serialization, and a typed invalid-signature failure path. This supports a compact offline trust model: only public keys are provisioned to the verifier; private signing keys remain in a dedicated operator-controlled vault record and never enter the renderer, extension archive, source tree, or CI logs.[^cryptography-ed25519]

The package signer and verifier need an identical byte sequence. Manifest JSON will therefore be parsed under strict constraints and canonicalized according to the JSON Canonicalization Scheme before signing or verification. JCS defines deterministic property sorting and UTF-8 serialization so semantically equivalent manifest documents produce an invariant cryptographic payload across supported environments.[^rfc8785]

The initial format will be a local `.aurx` ZIP archive with a single `manifest.json`, a detached `manifest.json.sig`, and an explicit payload-digest index for every executable or resource file. Signing only the manifest would leave entrypoint content replaceable, so the manifest must bind each package path to a SHA-256 digest, normalized POSIX path, and size. The verifier will reject duplicate names, traversal, symlinks, unexpected top-level files, malformed encodings, untrusted/revoked keys, digest mismatches, and invalid signatures before extraction, registration, enablement, or Docker execution.

The selected canonicalization dependency is the maintained `rfc8785` package, which exposes `dumps` for RFC 8785 bytes and explicit canonicalization errors for unsupported number values. It will be pinned with the backend dependencies and exercised with cross-process fixture vectors; generic JSON serialization will not be treated as a canonicalization substitute.[^python-rfc8785]

[^cryptography-ed25519]: [PyCA cryptography — Ed25519 signing](https://cryptography.io/en/latest/hazmat/primitives/asymmetric/ed25519/)
[^rfc8785]: [RFC 8785 — JSON Canonicalization Scheme](https://datatracker.ietf.org/doc/html/rfc8785)
[^python-rfc8785]: [Trail of Bits — rfc8785 Python API documentation](https://trailofbits.github.io/rfc8785.py/)
