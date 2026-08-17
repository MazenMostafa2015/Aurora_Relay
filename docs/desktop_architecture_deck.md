# Aurora Relay Desktop Application
## Architecture & Runtime Integration Strategy

### Slide 1 — Title
**Aurora Relay**  
Desktop architecture and runtime integration strategy

Subtitle: A local-first AI command center with MCP orchestration, a secure Electron shell, and fail-closed execution.

Visual direction: dark graphite canvas, cyan relay mark, thin amber signal line, restrained editorial typography.

### Slide 2 — Product thesis
**One workspace. Many capabilities. Explicit control.**

Aurora Relay turns a natural-language goal into a visible, inspectable workflow. The user sees the task, the plan, tool calls, approvals, and outcomes rather than receiving an opaque automation result.

Three product commitments:

| Commitment | Design consequence |
| --- | --- |
| Local-first | Ollama is preferred for on-device inference; cloud providers are opt-in. |
| Composable | MCP servers expose discoverable tools behind a router and registry. |
| Fail-closed | Code execution requires a healthy Docker runtime; host execution is never the fallback. |

### Slide 3 — Layered system architecture
**From intent to controlled action**

Show a five-layer diagram with directional arrows:

1. **Experience layer:** React dashboard, Electron shell, REST API, and WebSocket stream.
2. **Agent layer:** Coordinator, Planner, Executor, Monitor, and memory/state components.
3. **MCP layer:** multi-server client, registry, discovery, JSON-RPC routing, and tool metadata cache.
4. **Capability layer:** Browser MCP, Filesystem MCP, Docker code executor, database and external API servers.
5. **Infrastructure layer:** SQLite/PostgreSQL, Redis, structured logs, Prometheus/Grafana, and per-user desktop storage.

Callout: Desktop mode packages the frontend and backend together, but keeps the backend loopback-only and the renderer privilege-minimized.

### Slide 4 — Task lifecycle
**A visible execution loop**

Show a horizontal flow:

`User goal → Coordinator → Plan → Approval boundary → MCP tool call → Observation → State update → Next step → Result`

Supporting detail:

- The Planner decomposes goals into dependency-aware steps.
- The Executor routes each step to the selected MCP tool.
- The Monitor streams progress and records failures.
- WebSocket updates keep the Aurora Relay workspace synchronized.
- The final result includes tool evidence and execution state, not only generated prose.

### Slide 5 — Desktop runtime lifecycle
**Electron is the local control plane**

Show a sequence diagram:

`Electron main process → choose random loopback port → spawn packaged FastAPI backend → wait for /health → load bundled React UI → create tray → run first-run checks`

Security boundary panel:

- Renderer: `nodeIntegration: false`, `contextIsolation: true`, Chromium sandbox enabled.
- Preload: minimal, explicit IPC bridge for status, quit, tray, setup, and validated external links.
- Backend: binds to `127.0.0.1`, stores mutable state in platform-specific user data directories, defaults to SQLite.
- Shutdown: Electron owns the backend process lifecycle and stops it during application exit.

### Slide 6 — Ollama integration strategy
**Local inference without silent installation**

Ollama is optional and preferred when the user wants prompts and results to remain local.

Flow diagram:

`First-run probe: ollama --version → ready / unavailable → local-model readiness flag`

Operating rules:

- Do not bundle or silently install Ollama; installation may require privileges, drivers, storage, and license review.
- Do not auto-pull a model; model choice and disk usage require explicit user consent.
- If missing, link to the official installer and allow safe continuation.
- Re-run the probe after installation or service startup.

Outcome: local inference is a capability that becomes ready only after a verified runtime check.

### Slide 7 — Docker integration and fail-closed execution
**Isolation is a prerequisite, not an optimization**

Flow diagram:

`docker version → healthy daemon? → enable sandboxed executor : keep code execution disabled`

Docker policy:

- Docker Desktop is the simplest path for Windows and macOS; Docker Engine is supported on Linux.
- A CLI binary alone is insufficient; the Docker server must respond successfully.
- The app never exposes the Docker daemon over TCP, disables endpoint security, or mounts broad host paths.
- Missing or inaccessible Docker never triggers host-shell fallback.
- Resource limits, network policy, filesystem boundaries, and audit logging remain enforced by the sandbox layer.

### Slide 8 — First-run onboarding experience
**Progressive disclosure with safe recovery**

Show four setup cards with a progress bar:

1. Secure workspace — create per-user configuration and privacy defaults.
2. Local model runtime — probe Ollama and explain local-model availability.
3. Execution sandbox — probe Docker and explain why execution may remain disabled.
4. Finish setup — save preferences and capability state.

Error-handling model:

| State | UI behavior | Capability result |
| --- | --- | --- |
| Ready | Green status and continue | Capability enabled. |
| Missing optional runtime | Amber state, official install link, retry | App continues; capability disabled. |
| Runtime unhealthy | Technical details and recovery guidance | Capability remains disabled. |
| Probe failure | Retry, diagnostics, safe continuation | No unsafe fallback. |

### Slide 9 — Packaging and release strategy
**Build once from source; release natively per platform**

Build pipeline diagram:

`React build → PyInstaller backend → Electron Builder → native installer → sign → smoke test → checksum → publish`

Artifact matrix:

| Platform | Installer | Native release requirement |
| --- | --- | --- |
| Windows | NSIS x64/arm64 | Windows runner and Authenticode signing. |
| macOS | DMG x64/arm64 | macOS runner, Developer ID signing, notarization. |
| Linux | AppImage + Debian x64/arm64 | Linux runner, package/repository signing policy. |

Callout: The source archive does not include Ollama, Docker, signing keys, notarization credentials, or generated dependencies.

### Slide 10 — Operational controls and roadmap
**Trust is a lifecycle, not a launch feature**

Current controls:

- JWT-authenticated API and WebSocket sessions.
- Structured logs, Prometheus metrics, Grafana dashboards, and release readiness gates.
- Per-user data paths, restrictive config permissions, loopback-only desktop backend.
- MCP registry/discovery with explicit tool routing.
- Docker-required execution with no host fallback.

Next release gates:

1. Native CI builds and clean-machine tests for Windows, macOS, and Linux.
2. Explicit Ollama model selection/download with disk-space checks.
3. Docker image preflight and sandbox compatibility tests.
4. Signed updater feed with rollback and artifact provenance.
5. Runtime upgrade policy and enterprise deployment playbook.

### Slide 11 — Reference implementation map
**Where the strategy lives in the repository**

| Concern | Key path |
| --- | --- |
| Electron lifecycle | `desktop/electron/main.js` |
| First-run orchestration | `desktop/electron/setup-wizard.js`, `setup.html` |
| Renderer IPC boundary | `desktop/electron/preload.js`, `setup-preload.js` |
| Backend desktop entrypoint | `backend/run.py` |
| Backend packaging | `desktop/pyinstaller/backend.spec` |
| Native build orchestration | `desktop/scripts/build-all.sh` |
| Installer targets | `desktop/electron/package.json` |
| Runtime strategy | `docs/runtime_installation.md` |
| Native installer guide | `docs/native_installers.md` |

### Slide 12 — Closing
**Aurora Relay makes capability visible, local by default, and safe under failure.**

Closing statement: The desktop application is not merely a wrapper around a web dashboard. It is a controlled local runtime that coordinates the UI, backend, MCP tools, inference providers, and sandbox boundary while making every important capability explicit to the user.

Footer references:

- Electron Builder documentation: https://www.electron.build/docs/
- Ollama downloads: https://ollama.com/download
- Docker Desktop documentation: https://docs.docker.com/desktop/
- Docker Engine installation: https://docs.docker.com/engine/install/
- Apple notarization: https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution
- Microsoft code signing: https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/code-signing-options
