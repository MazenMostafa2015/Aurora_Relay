# Windows installer CI/CD and signing

## Purpose

The Windows release pipeline builds the Aurora Relay frontend, freezes the FastAPI/MCP backend with PyInstaller, packages the Electron shell as an NSIS installer for x64 and arm64, signs the resulting executables, generates checksums, creates GitHub artifact attestations, and publishes a release only after signing succeeds.

The workflow is defined in `.github/workflows/release-windows.yml`. It runs on version tags such as `v0.8.0` and can also be started manually through `workflow_dispatch`. Pull requests continue to use the existing validation workflow; release signing is isolated behind the `release` environment.

## Pipeline stages

| Stage | Runner | Purpose | Release gate |
|---|---|---|---|
| Validate | Ubuntu | Compile and test the backend, install frontend dependencies, run type/build validation | Must pass before Windows work starts |
| Build | Windows | Build the frontend, freeze the backend, install Electron dependencies, create NSIS x64/arm64 artifacts | Must produce installer executables |
| Sign | Windows | Sign every `.exe` with SHA-256 and a trusted timestamp, then verify with `signtool verify /pa /all` | Any failure stops release |
| Integrity | Windows | Create `SHA256SUMS` and preserve blockmaps | Hash file must match published artifacts |
| Provenance | GitHub Actions | Create signed artifact attestations for release executables | Requires `id-token: write` and `attestations: write` |
| Publish | Windows | Upload artifacts and create a GitHub Release on a version tag or approved manual run | Requires protected `release` environment |

GitHub describes artifact attestations as cryptographically signed provenance claims connecting an artifact to its workflow, repository, environment, commit, and trigger. Consumers should verify those attestations rather than treating their existence as sufficient on its own. [1]

## Required repository and environment configuration

Create a protected GitHub environment named `release`. Require reviewer approval for production publication, restrict deployment branches or tags, and keep the signing credentials unavailable to pull requests. The workflow uses the following secrets and variables:

| Name | Type | Purpose |
|---|---|---|
| `WINDOWS_SIGNING_PFX_BASE64` | Environment secret | Base64-encoded code-signing certificate container |
| `WINDOWS_SIGNING_PFX_PASSWORD` | Environment secret | Password for the certificate container |
| `WINDOWS_TIMESTAMP_URL` | Environment variable | RFC 3161 trusted timestamp service URL |
| `AURORA_UPDATE_FEED` | Environment variable/secret | Signed update feed configured separately from build validation |

The PFX is reconstructed only in the ephemeral runner’s temporary directory and deleted in a `finally` block. Never commit a PFX, private key, password, token, or certificate material to the repository. Prefer a managed signing service such as Microsoft Artifact Signing when the organization has the required identity, policy, and tenant setup; in that model the signing step should exchange short-lived identity credentials rather than storing a long-lived private key in GitHub.

## Windows runner prerequisites

The `windows-latest` runner must provide the Windows SDK `signtool.exe`, Python 3.12, Node.js 22, pnpm 10.4.1, and the package-manager dependencies required by the repository. The workflow installs Python and Node dependencies itself. Electron Builder’s Windows NSIS target may need additional native tooling or a pinned runner image if the project later adds custom native modules.

The build uses the repository layout expected by `desktop/scripts/build-all.sh`:

```powershell
$env:FRONTEND_DIR = "$env:GITHUB_WORKSPACE\frontend"
$env:PYTHON = "python"
 bash desktop/scripts/build-all.sh win
```

The produced files are written to `desktop/release`. The build contains the compiled application and frozen backend, not Node.js or Python runtimes for end users.

## Signing policy

Sign the Aurora Relay NSIS installer and any signed native bootstrapper executable after packaging and before checksums or publication. Use SHA-256 file digests, SHA-256 signatures, and a trusted RFC 3161 timestamp. Immediately verify every executable with `signtool verify /pa /all`. A failed or missing signature must prevent release publication; unsigned installers should be available only as internal CI artifacts, never as public release assets.

The prerequisite bootstrapper is a separate trust boundary. If a native `Aurora-Relay-Setup.exe` wrapper is introduced, sign it with the same release policy and have it display the selected third-party packages, license links, privilege requirements, and restart implications before installation. It may invoke official Ollama and Docker installation channels only with explicit user or administrator consent. It must never silently install third-party software or make Docker’s daemon available over an unauthenticated TCP socket.

## Release promotion model

Every pull request runs validation only. A version tag starts the release workflow but pauses at the protected `release` environment before publication. A reviewer verifies the source commit, dependency lockfiles, release notes, signing certificate validity, package IDs, and runtime installation policy. After approval, the workflow signs, attests, hashes, uploads, and publishes the release.

For emergency rollback, mark the GitHub Release as a pre-release or draft, remove its update-feed entry, and publish the previous known-good version. Because the desktop updater is inert unless `AURORA_UPDATE_FEED` is configured, a deployment team can stage artifacts without enabling automatic update consumption.

## Verification commands

A release operator can verify the installer signature and checksum on Windows:

```powershell
signtool verify /pa /all .\Aurora-Relay-0.8.0-win-x64.exe
Get-FileHash .\Aurora-Relay-0.8.0-win-x64.exe -Algorithm SHA256
Get-Content .\SHA256SUMS
```

A consumer or release auditor can verify GitHub provenance with the GitHub CLI after downloading the artifact:

```bash
gh attestation verify Aurora-Relay-0.8.0-win-x64.exe --repo OWNER/REPOSITORY
```

The exact command and repository selector should follow the repository’s GitHub policy and current CLI version. Attestation verification is complementary to Authenticode signature verification, not a replacement for it.

## What is not automated by this workflow

The workflow does not silently install Ollama or Docker Desktop on the runner or end-user machine. It packages Aurora Relay only; runtime installation remains an explicit onboarding or enterprise endpoint-management decision. Docker must be healthy before sandboxed execution is enabled, and the application must remain fail-closed if Docker is unavailable. Ollama is optional and can be installed through official vendor channels or an organization-approved software catalog.

The workflow also does not provide a production signing certificate, notarization authority, SmartScreen reputation, an update feed, or a legal license decision for third-party runtimes. Those are release-owner prerequisites.

## References

[1]: https://docs.github.com/en/actions/concepts/security/artifact-attestations "GitHub Artifact attestations"
[2]: https://learn.microsoft.com/en-us/windows/win32/msi/windows-installer-portal "Microsoft Windows Installer portal"
[3]: https://learn.microsoft.com/en-us/visualstudio/deployment/creating-bootstrapper-packages?view=visualstudio "Microsoft Create bootstrapper packages"
[4]: https://learn.microsoft.com/en-us/windows/package-manager/winget/ "Microsoft winget documentation"
[5]: https://www.electron.build/docs/configuration "Electron Builder configuration"
