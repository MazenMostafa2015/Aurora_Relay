# Production Readiness Checklist

## Verified in the current workspace

- [x] Backend modules compile successfully.
- [x] Existing backend, MCP, sandbox, and API tests are retained.
- [x] Phase 8 deterministic integration fixtures and tests are present.
- [x] Frontend Playwright configuration and smoke scenarios are present.
- [x] Frontend type checking and production build are available through `pnpm validate`.
- [x] Backend exposes `/health` and Prometheus-compatible `/metrics`.
- [x] Structured JSON request logging is enabled in the application.
- [x] Dockerfiles run backend/frontend processes without root privileges.
- [x] Compose includes PostgreSQL, Redis, backend, frontend, Prometheus, and Grafana with health-gated dependencies.
- [x] CI configuration covers backend, frontend, Compose syntax, and filesystem vulnerability scanning.
- [x] Environment template, deployment guide, user guide, and developer guide are present.

## Must be verified in a deployment environment

- [ ] CI passes with the repository’s actual lockfiles and dependency mirrors.
- [ ] PostgreSQL migrations are reviewed and run against a disposable staging database.
- [ ] Redis-backed rate limiting/session behavior is enabled and tested.
- [ ] TLS, DNS, secret manager integration, backup restoration, and alert routing are verified.
- [ ] Playwright browsers are installed and all E2E scenarios pass against the deployed frontend.
- [ ] Load testing meets the agreed p95 latency, error-rate, and concurrency thresholds.
- [ ] Bandit, pip-audit, pnpm audit, Trivy, and secret scanning have no unaccepted findings.
- [ ] Sandbox execution is isolated from the API tier and receives no host Docker socket.
- [ ] Ollama/provider credentials and model availability are verified without exposing secrets to the frontend.
- [ ] Grafana access is private and dashboards receive real Prometheus samples.

## Release decision

The system is **deployment-prepared but not production-certified** until the environment-specific checks above pass. Record every exception with an owner, mitigation, and expiry date. A successful local Compose startup is not evidence that backups, TLS, external identity, rate-limit distribution, or sandbox isolation are production-ready.


## Desktop packaging readiness

The repository now contains a desktop packaging foundation under `desktop/`. The Electron shell starts the FastAPI backend on loopback, serves the bundled React build through the backend, uses per-user SQLite/config/log paths, and keeps renderer privileges isolated. The first-run wizard defaults to local Ollama usage, while the updater remains disabled unless a trusted signed update feed is configured.

| Gate | Status | Evidence or remaining action |
| --- | --- | --- |
| Electron renderer isolation and minimal preload bridge | Pass | `desktop/electron/main.js`, `preload.js`, and `setup-preload.js` use context isolation, disabled Node integration, and sandboxed renderers. |
| Packaged backend entry point and local data paths | Pass | `backend/run.py` creates per-user directories and defaults to SQLite. |
| Frontend bundling into the local service | Pass | Optional `AURORA_FRONTEND_DIR` serving is implemented in `backend/app/main.py`. |
| Cross-platform Electron Builder targets | Conditional | Configuration exists for Windows NSIS, macOS DMG, Linux AppImage, and Debian; platform-native builds remain to be run in CI. |
| Windows signing and macOS signing/notarization | Remaining follow-up | Requires organization certificates, secrets, and native release runners. |
| Signed auto-update feed | Remaining follow-up | Set `AURORA_UPDATE_FEED` only after publishing signed artifacts and validating rollback behavior. |
| Ollama distribution | Remaining follow-up | Ollama is not bundled by default; define a legal distribution and installation strategy before promising a single-download offline experience. |
| Docker sandbox availability | Remaining follow-up | Desktop packaging does not bypass the fail-closed sandbox policy; validate Docker or an approved alternative on each target OS. |

The desktop build is therefore **configuration-ready, not release-certified**. Do not distribute installers as production artifacts until native packaging, signing, update, sandbox, and clean-machine installation tests pass.


## Runtime onboarding readiness

The desktop first-run flow now probes `ollama --version` and `docker version` with bounded timeouts, reports progress independently, links users to official installation guidance, and permits safe continuation when optional runtimes are missing. The persisted runtime state records whether local-model inference and code execution are actually enabled.

| Gate | Status | Remaining validation |
| --- | --- | --- |
| Visual progress indicator and per-runtime states | Pass | Setup UI and `setup:progress` IPC events are implemented. |
| Detailed error handling and retry | Pass | Missing binaries, unavailable Docker daemon, command failures, and unexpected probe errors have distinct messages and technical details. |
| Ollama installation strategy | Pass | End-user and enterprise guidance is documented in `docs/runtime_installation.md`. |
| Docker installation strategy | Pass | Desktop versus Linux Engine paths, permissions, and fail-closed behavior are documented. |
| Native runtime detection on supported operating systems | Conditional | Run first-run tests on Windows, macOS, and Linux with runtimes installed, stopped, missing, and permission-restricted. |
| Model pull and Docker image preflight UX | Remaining follow-up | Add explicit user-confirmed model/image download actions with disk-space reporting before enabling those workflows. |
| Runtime upgrade and rollback behavior | Remaining follow-up | Define version compatibility policy and test runtime upgrades independently from Aurora Relay updates. |
