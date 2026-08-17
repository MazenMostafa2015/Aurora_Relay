# Native Installer Build Guide

This guide explains how to turn the Aurora Relay desktop source archive into native installers for Windows, macOS, and Linux. The repository uses a two-stage build: the React frontend is compiled first, the FastAPI/MCP backend is frozen into a local executable with PyInstaller, and Electron Builder packages both into a platform installer.

> The commands below create native application artifacts. They do not install Ollama or Docker, and they do not automatically create trusted code-signing identities. Those runtimes and release credentials are deliberately managed outside the Aurora Relay installer.

## Build inputs and artifact map

| Component | Source | Build output | Purpose |
| --- | --- | --- | --- |
| React UI | `/home/ubuntu/frontend` or `FRONTEND_DIR` | `frontend/dist/public` | Bundled renderer assets served by the local FastAPI process. |
| FastAPI/MCP backend | `backend/run.py`, `backend/app`, `mcp_servers` | `desktop/backend-dist/aurora-backend` | Loopback-only local service with per-user SQLite/config/log paths. |
| Electron shell | `desktop/electron` | `desktop/release/` | Window, tray, preload bridge, first-run setup, updater, and installer wrapper. |
| Native installer | Electron Builder configuration | Windows NSIS, macOS DMG, Linux AppImage and Debian | User-facing installation artifacts. |

Electron Builder is the packaging engine for these targets and documents the general configuration and multi-platform model in its official documentation.[1] The project’s `desktop/electron/package.json` sets the product ID to `com.aurora.relay`, enables ASAR packaging, adds the frozen backend and frontend as extra resources, and defines x64 and arm64 targets.

## Common prerequisites

Use a clean checkout or the extracted source archive. Install Python 3, Node.js, pnpm, and a working C/C++ toolchain suitable for the Python dependencies used by the backend. Install the backend requirements into an isolated Python environment, and install PyInstaller in that same environment. Install the Electron dependencies from `desktop/electron/package.json` through pnpm.

```bash
cd /path/to/mcp-aplication-36e0710f
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
python -m pip install pyinstaller

cd desktop/electron
pnpm install
pnpm lint:syntax
cd ../..
```

The build script expects the frontend project at `/home/ubuntu/frontend` by default. When using the archive on another machine, set `FRONTEND_DIR` explicitly:

```bash
export FRONTEND_DIR=/path/to/frontend
```

The script removes its generated staging directories before each build. It creates `desktop/frontend-dist`, `desktop/backend-dist`, `desktop/.pyinstaller`, and `desktop/release`; these should not be committed to source control.

## Build the frontend and backend separately

A useful diagnostic mode is the directory package. It exercises the frontend build, PyInstaller spec, resource copying, and Electron packaging without first creating a signed installer.

```bash
cd /path/to/mcp-aplication-36e0710f
FRONTEND_DIR=/path/to/frontend desktop/scripts/build-all.sh dir
```

The sequence is:

1. Run `pnpm build` in the frontend project.
2. Copy `frontend/dist/public` into `desktop/frontend-dist`.
3. Run PyInstaller with `desktop/pyinstaller/backend.spec` and emit the backend executable into `desktop/backend-dist`.
4. Install desktop dependencies with pnpm.
5. Run Electron Builder in directory mode.

Before moving to installers, verify that `desktop/backend-dist` contains the expected executable and that the packaged frontend contains `index.html` and its asset directory. Start the directory package on the target operating system and confirm that the local service binds only to `127.0.0.1`, the setup window appears, and `/health` becomes ready before the main window loads.

## Windows NSIS installer

Build the Windows installer on a Windows x64 or arm64 runner. The repository target is an Electron Builder NSIS installer with a non-one-click flow, an optional installation directory, Start Menu shortcut, and desktop shortcut.

```powershell
cd C:\path\to\mcp-aplication-36e0710f
$env:FRONTEND_DIR = 'C:\path\to\frontend'
& .\desktop\scripts\build-all.sh win
```

If Bash is not available on the Windows runner, run the equivalent stages manually from PowerShell: build the frontend with `pnpm build`, invoke PyInstaller against `desktop/pyinstaller/backend.spec`, and run `pnpm build:win` from `desktop/electron`.

The expected artifact is similar to `desktop/release/Aurora-Relay-0.8.0-win-x64.exe`; the exact filename includes the configured version, operating system, and architecture. Sign the installer and any executable payloads in the Windows release pipeline before distribution. Microsoft documents code-signing options and Smart App Control considerations for Windows applications.[2] Keep the certificate private key in a CI secret store or hardware-backed signing service; never commit it to the archive.

Validate on a clean Windows machine by installing per-user, launching Aurora Relay, confirming the firewall prompt is not converted into a public-network service, checking tray behavior, closing the app, and verifying that the local backend process exits. Test both a machine with Docker/Ollama available and a machine with neither runtime installed.

## macOS DMG

Build and sign the macOS package on macOS. The project requests x64 and arm64 DMG targets. For a universal distribution strategy, run native builds for each architecture or use a controlled universal packaging workflow after verifying all embedded dependencies.

```bash
cd /path/to/mcp-aplication-36e0710f
export FRONTEND_DIR=/path/to/frontend
./desktop/electron/installer/mac/build.sh
```

The wrapper calls `pnpm build:mac` and refuses to run on a non-Darwin host. The direct equivalent is:

```bash
cd desktop/electron
pnpm build:mac
```

Set the Electron Builder signing environment according to the organization’s certificate-management policy. The release job must sign the app bundle and DMG, then submit the result to Apple’s notarization service and staple the notarization ticket before publishing. Apple’s official guidance covers notarizing software distributed outside the Mac App Store and customizing a notarization workflow.[3] [4]

The expected artifacts are similar to `desktop/release/Aurora-Relay-0.8.0-mac-x64.dmg` and `Aurora-Relay-0.8.0-mac-arm64.dmg`. Validate Gatekeeper behavior on a clean macOS machine, including first launch, quarantine handling, tray behavior, app update behavior, and shutdown of the embedded backend.

## Linux AppImage and Debian packages

Build Linux artifacts on a supported Linux runner. The project produces both AppImage and Debian targets for x64 and arm64.

```bash
cd /path/to/mcp-aplication-36e0710f
export FRONTEND_DIR=/path/to/frontend
./desktop/electron/installer/linux/build.sh
```

The direct equivalent is:

```bash
cd desktop/electron
pnpm build:linux
```

The expected artifacts are similar to `Aurora-Relay-0.8.0-linux-x64.AppImage` and `Aurora-Relay-0.8.0-linux-x64.deb`. Test the AppImage on a clean supported distribution and test the Debian package on an Ubuntu/Debian staging image. Verify desktop entry registration, icon display, per-user data paths, application shutdown, and behavior when the Docker daemon is stopped or inaccessible.

Linux package signing, repository metadata, and update distribution are release-policy decisions. If Debian packages are distributed through an APT repository, sign repository metadata and publish checksums over HTTPS. If AppImage artifacts are distributed directly, sign or otherwise attest the release according to the organization’s supply-chain policy.

## Build all configured targets

The `all` target invokes Electron Builder’s configured platform targets. It is suitable for a native CI runner only when the runner and signing configuration support the requested output.

```bash
cd /path/to/mcp-aplication-36e0710f
FRONTEND_DIR=/path/to/frontend desktop/scripts/build-all.sh all
```

Do not treat `all` on Linux as proof that trustworthy Windows and macOS releases have been produced. Electron Builder supports multiple platform workflows, but native signing, notarization, operating-system integration, and clean-machine behavior must be validated on the respective release platforms.[1]

## CI release pattern

Use separate jobs for Linux, Windows, and macOS. Each job checks out the same commit, installs the same locked frontend and desktop dependencies, builds the frontend, freezes the backend, packages the native installer, signs the artifact, runs platform smoke tests, generates SHA-256 checksums, and uploads the installer plus release metadata. Keep publishing and auto-update feed promotion as a protected environment step after human approval.

The minimum release matrix is:

| Job | Runner | Targets | Protected secrets |
| --- | --- | --- | --- |
| Linux release | Ubuntu | AppImage, Debian | Repository signing key, update-feed credentials if enabled. |
| Windows release | Windows | NSIS x64 and arm64 | Authenticode certificate or signing service credentials. |
| macOS release | macOS | DMG x64 and arm64 | Apple Developer ID certificate, notarization credentials, and provider configuration. |

## Runtime boundaries

Ollama and Docker are not bundled by this source package. The first-run wizard detects them with bounded local probes, provides official installation links, and supports retry. Ollama is optional and controls local-model readiness. Docker is required for code-execution tools; if it is unavailable, the application remains fail-closed and never substitutes host execution. See [`runtime_installation.md`](runtime_installation.md) for the end-user installation and enterprise deployment strategy.

## Release checklist

Before publishing an installer, confirm that the archive was built from a clean commit, generated directories were removed before packaging, dependency and license review is complete, native signatures verify, checksums match, and the installer works on a clean machine. Confirm that first-run setup handles four states: both runtimes ready, Ollama missing, Docker missing, and both runtimes missing. Confirm that the local backend cannot be reached through a non-loopback bind, that untrusted code cannot execute without Docker, and that updater publishing is disabled until the signed feed is ready.

## References

[1]: https://www.electron.build/docs/ "electron-builder documentation"
[2]: https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/code-signing-options "Microsoft code-signing options for Windows apps"
[3]: https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution "Apple: Notarizing macOS software before distribution"
[4]: https://developer.apple.com/documentation/security/customizing-the-notarization-workflow "Apple: Customizing the notarization workflow"
