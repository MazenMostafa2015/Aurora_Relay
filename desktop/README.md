# Aurora Relay Desktop Foundation

Aurora Relay uses **Option A: an Electron shell with an embedded local FastAPI service**. The desktop process starts the packaged Python backend on a randomized loopback port, waits for `/health`, and loads the bundled React application from that service. Mutable state is stored in the platform-appropriate per-user application-data directory, with SQLite as the local database default.

The Electron renderer runs with `nodeIntegration: false`, `contextIsolation: true`, and Chromium sandboxing enabled. The preload bridge exposes only status, tray, quit, and explicitly validated external-link operations. The backend binds to `127.0.0.1`; it is not intended to be a network-facing production service. The code-execution sandbox remains fail-closed: desktop packaging does not bypass Docker or substitute host execution when Docker is unavailable.

## Build workflow

The build requires Python 3, Node.js, pnpm, and PyInstaller. Set `FRONTEND_DIR` when the React project is not at `/home/ubuntu/frontend`.

```bash
cd /path/to/mcp-aplication-36e0710f
FRONTEND_DIR=/path/to/frontend desktop/scripts/build-all.sh dir
```

Use `win`, `mac`, `linux`, or `all` instead of `dir` to request platform artifacts. Windows signing, macOS signing/notarization, and update publishing require credentials and must run in their respective platform CI environments. The Linux build produces AppImage and Debian targets through Electron Builder; RPM should be added only when the target distribution policy is known.

## Local development

Install desktop dependencies and start the shell only after the frontend has a production build available:

```bash
cd desktop/electron
pnpm install
pnpm lint:syntax
pnpm start
```

The desktop shell starts `backend/run.py` in development mode. It expects the repository backend dependencies to be installed in the selected Python environment and uses the separately built frontend directory supplied through the launcher.

## First run and updates

The first-run wizard defaults to local Ollama inference and leaves cloud providers and anonymous diagnostics disabled. Preferences are written with restrictive file permissions. The updater is deliberately inert unless `AURORA_UPDATE_FEED` is configured; release artifacts must be signed and published through a trusted update feed before enabling it.

## Release gates and limitations

The repository can validate syntax, Python compilation, frontend builds, and configuration locally. It cannot produce trustworthy Windows or macOS installers from Linux alone, and it cannot validate code signing, notarization, SmartScreen reputation, or platform auto-update behavior without the corresponding release credentials and runners. Ollama is not bundled by this foundation; users install it separately or an organization provides a licensed distribution strategy. Docker is also not bundled, so sandboxed code execution must report unavailable rather than fall back to host execution.


## End-user runtime onboarding

See [`docs/runtime_installation.md`](../docs/runtime_installation.md) for the supported Ollama and Docker installation paths. The setup window performs bounded local probes rather than installing third-party runtimes silently. It shows a staged progress bar, independent status cards, detailed command output, official installation links, and a retry action. Users can continue without Ollama, but local model selection is unavailable until Ollama is detected. Users can continue without Docker, but code execution remains disabled because the sandbox is fail-closed.

The recommended support workflow is to ask the user to install the runtime through the official vendor package or the organization’s endpoint-management system, start the service, and then select **Retry checks**. Do not ask users to expose Docker’s daemon over TCP, disable endpoint security, add broad filesystem mounts, or run untrusted code with a host shell. On Linux, Docker group membership should be treated as privileged access and managed by the administrator.

## Windows single-file deployment

Aurora Relay is not distributed as a `.SP1` file because that extension is not a standard application-installer format in Windows Installer. The supported native Windows artifact is the signed Electron Builder NSIS executable. For an operator-controlled one-file prerequisite flow, use `installer/windows/prereq-bootstrap.ps1` or wrap the same logic in a signed native bootstrapper. It can install Ollama and/or Docker Desktop through `winget` only when explicitly selected, then launch the Aurora Relay installer. See `../docs/windows_single_file_deployment.md` for consent, licensing, elevation, rollback, and fail-closed requirements.
