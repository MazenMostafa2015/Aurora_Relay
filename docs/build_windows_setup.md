# Building the Aurora Relay Windows Setup Executable

## Scope

This source tree is configured to produce a native **Windows x64 NSIS setup executable**. The target artifact is created under `desktop/release/` as `Aurora-Relay-<version>-win-x64.exe`. A Linux host must not build this target: PyInstaller freezes the backend for the host operating system, so a Linux-generated backend would not run inside a Windows installer. The build script now rejects this unsafe cross-build path deliberately.

## Recommended: protected GitHub Actions release build

Push the self-contained source tree to the repository that contains `.github/workflows/release-windows.yml`. Configure the repository’s protected `release` environment with `WINDOWS_SIGNING_PFX_BASE64`, `WINDOWS_SIGNING_PFX_PASSWORD`, and `WINDOWS_TIMESTAMP_URL`. The PFX must belong to the organization’s code-signing certificate; never commit it or place it in the installer source.

Create and push a version tag, for example `v0.8.0`. The workflow validates the backend and frontend, builds the Python backend natively on `windows-latest`, packages NSIS, signs executable artifacts, verifies signatures, creates SHA-256 checksums and a provenance attestation, then uploads the release artifacts. The installer must be taken only from the signed workflow artifact or GitHub Release.

## Native Windows workstation build

Use a clean Windows 11 x64 build machine with Python 3.12, Node.js 22, pnpm 10, Git for Windows (including Bash), and a code-signing certificate available to the signing helper. From Git Bash at the repository root, run:

```bash
bash desktop/scripts/build-all.sh win
```

Then sign and verify artifacts in PowerShell using the organization’s protected certificate inputs:

```powershell
./desktop/scripts/sign-windows.ps1 `
  -ReleaseDirectory desktop/release `
  -PfxBase64 $env:WINDOWS_SIGNING_PFX_BASE64 `
  -PfxPassword $env:WINDOWS_SIGNING_PFX_PASSWORD `
  -TimestampUrl $env:WINDOWS_TIMESTAMP_URL

Get-AuthenticodeSignature .\desktop\release\*.exe
Get-FileHash .\desktop\release\*.exe -Algorithm SHA256
```

## Release checks

The signed installer must be tested on a clean Windows VM before distribution. Confirm first-launch JWT provisioning succeeds, the frontend has no `__manus__` or debug collector asset, no shipped value contains `change-me-in-production`, the backend binds only to loopback, and code execution remains disabled when Docker is absent. Verify the installer’s Authenticode status is `Valid` and publish its SHA-256 checksum with the artifact.

## Runtime boundaries

The setup executable bundles Aurora Relay’s Electron shell, production frontend, frozen Python backend, MCP configuration, and runtime defaults. It does not silently install Docker Desktop, Ollama, or LLM models. The separate prerequisite bootstrapper may offer explicit, consent-based `winget` installation for those runtimes after the signed application installer is available.
