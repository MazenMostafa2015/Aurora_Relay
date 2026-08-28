# Aurora Relay v0.8.23 — Release Notes Draft

**Release status:** Draft for the protected release workflow.  
**Target:** Current `main` after the validated documentation commit.  
**Scope:** Changes since v0.8.22.

## Summary

Aurora Relay v0.8.23 consolidates the signed-extension, operations-health, interaction-reliability, and documentation improvements delivered after v0.8.22. The release strengthens local operator feedback without weakening the local-first, Docker-only execution, protected credential, or explicit-approval boundaries.

## Highlights

| Area | Included update |
|---|---|
| Signed extensions | `.aurx` packages are verified with the local Ed25519 trust root before installation, enablement, or execution. Tampered, unsigned, unknown-key, and revoked packages fail closed. |
| Operational health | Authenticated health history supports 7-, 30-, and 90-day retention periods and is exposed through the lazy-loaded operations dashboard. |
| Interaction reliability | API handling accepts legitimate empty `204 No Content` responses, invalid nested agent-loop controls were replaced with semantic buttons, and blocked actions now surface explicit authentication or validation feedback. |
| Workspace navigation | A dedicated Playwright regression verifies all nine workspace destinations: Overview, Task desk, Tool explorer, Connectors, Operations, Extensions, Agent loop, Release evidence, and Settings. |
| Connector resilience | Connector operations use bounded retry, timeout, and backoff behavior, with owner-scoped limits for sensitive operations and clearer recovery messages. |
| Performance and usability | Operational lists are bounded to avoid unbounded renderer growth, and priority views use accessible asynchronous status and retry patterns. |
| Local runtime guidance | The audit documents the verified development API path, loopback CORS expectations, Electron-selected backend port lifecycle, and why port `5000` must not be assumed. |

## Validation Evidence

The complete Playwright suite passed with **17 tests** on the v0.8.23 preparation branch. The focused workspace-navigation regression also passed. Previous evidence retained in the interaction audit records passing backend, TypeScript, production-build, offline-renderer, visual-regression, and Electron syntax gates for the included implementation series.

## Known Boundaries

The `503.92 kB` framework-chunk advisory remains intentionally non-blocking and unchanged. It does not affect control behavior and is not addressed by this release. No CDN, remote telemetry, host-execution fallback, automatic merge, or automatic deployment is introduced.

The protected Windows workflow remains responsible for producing and validating signed installer assets, checksums, provenance, and clean-machine evidence after the tag is pushed. Native installer release status must be determined from that workflow’s resulting evidence rather than inferred from source validation alone.

## Upgrade Notes

Operators should launch the desktop application through Electron so it can select its local loopback port, provision the per-install runtime secret, wait for `/health`, and load the matching renderer. For development sessions, configure the renderer’s `VITE_API_BASE_URL` to the active local API origin and keep CORS, database, host-validation, and JWT settings aligned with that origin.

Existing extensions must be repackaged and signed through the approved local signing workflow before they can be enabled. Docker remains mandatory for extension code execution; unavailable Docker disables execution rather than falling back to the host.
