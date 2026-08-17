# Windows single-file deployment strategy

## Decision

Aurora Relay should not be distributed as a file named `.SP1`. `.SP1` is not a standard application-installer extension in the Windows Installer model. The supported native artifact is a **signed Electron Builder NSIS setup executable**. If one file must install selected prerequisites and then deploy Aurora Relay, use a signed PowerShell or native bootstrapper wrapper around the NSIS installer, or use a Microsoft/Visual Studio bootstrapper package with explicit manifests.

The repository now includes `desktop/electron/installer/windows/prereq-bootstrap.ps1` as a transparent bootstrapper option. It can install Ollama and/or Docker Desktop through `winget` only when the operator explicitly passes the corresponding switches, then launches the Aurora Relay installer. It does not silently install third-party software, download arbitrary binaries, or execute code on the host.

## What the end user actually needs

The packaged Aurora Relay installer contains the Electron shell, the compiled React frontend, and the PyInstaller-frozen FastAPI/MCP backend. End users do **not** need Node.js, Python, pnpm, PyInstaller, or Docker to launch the desktop application itself.

Ollama is optional and provides local inference. Docker Desktop is required only for sandboxed code execution. The application performs health checks during first run and keeps each capability disabled until its runtime is verified. Docker unavailability must never trigger host-shell execution.

| Component | Install policy | Required for launch | Required for capability |
|---|---|---:|---|
| Aurora Relay NSIS installer | Bundle in the signed release | Yes | All desktop features |
| Ollama | Optional, user/admin consent | No | Local inference |
| Docker Desktop | Optional for basic launch, explicit consent | No | Sandboxed code execution |
| Node.js/Python/PyInstaller | Build-machine only | No | Creating installers |
| winget/App Installer | Optional bootstrapper dependency | No | Automatic prerequisite installation |

## Recommended release options

### Option A: Aurora Relay installer only

Ship the signed NSIS executable and let first-run onboarding link to the official Ollama and Docker installation paths. This is the safest default for consumer and enterprise environments because third-party licenses, restarts, virtualization settings, and administrator approval remain visible.

### Option B: Signed Windows bootstrapper

Ship a signed `Aurora-Relay-Setup.exe` bootstrapper that checks for `winget`, displays the selected prerequisite list, requests consent, installs only selected package IDs, and then launches the signed Aurora Relay NSIS installer. The included PowerShell script is suitable as an operator-controlled foundation, but production distribution should wrap it in a signed native bootstrapper or enterprise deployment tool rather than relying on a raw `.ps1` download.

Example operator flow from an elevated PowerShell session:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\prereq-bootstrap.ps1 -AppInstaller .\Aurora-Relay-0.8.0-win-x64.exe -InstallOllama -InstallDocker
```

For an application-only deployment:

```powershell
.\prereq-bootstrap.ps1 -AppInstaller .\Aurora-Relay-0.8.0-win-x64.exe -SkipPrerequisites
```

The exact winget package IDs should be revalidated in the release environment before publishing because package sources, publisher identifiers, and enterprise policy can change.

### Option C: Enterprise bootstrapper or software distribution

For managed fleets, use Intune, Configuration Manager, Group Policy, or a Microsoft/Visual Studio bootstrapper package. This allows administrators to stage Docker Desktop, Ollama, and Aurora Relay under an approved software policy, while the desktop application still reports runtime readiness and remains fail-closed.

## Security and operations requirements

The bootstrapper must show the list of third-party packages, license links, expected download sizes where available, privilege requirements, and restart implications before installation. It must log package identifiers and exit codes without logging credentials or tokens. It must stop on a failed prerequisite installation and offer retry, manual-install guidance, or application-only continuation.

Docker Desktop may require administrator approval, virtualization support, WSL 2 or Hyper-V configuration, and a restart. Ollama may run as a per-user or machine-managed service depending on the selected installation policy. Neither runtime should be bundled inside Aurora Relay without a separate legal, update, and vulnerability-management decision.

The production release must use a native Windows signing certificate for the bootstrapper and NSIS installer, verify SHA-256 checksums, test on clean Windows x64 and arm64 machines, exercise missing/stopped/permission-restricted runtime cases, and publish rollback instructions. A renamed `.SP1` file does not provide these properties.

## References

[1]: https://learn.microsoft.com/en-us/windows/win32/msi/windows-installer-portal "Microsoft Windows Installer portal"
[2]: https://learn.microsoft.com/en-us/visualstudio/deployment/creating-bootstrapper-packages?view=visualstudio "Microsoft Create bootstrapper packages"
[3]: https://learn.microsoft.com/en-us/windows/package-manager/winget/ "Microsoft winget documentation"
[4]: https://ollama.com/download "Ollama official downloads"
[5]: https://docs.docker.com/desktop/ "Docker Desktop documentation"
[6]: https://www.electron.build/docs/configuration "Electron Builder configuration"

The distinction between standard Windows Installer packages, bootstrapper prerequisite flows, and the Aurora Relay NSIS artifact is grounded in the Microsoft documentation above. [1] [2] The third-party runtime links are provided for official installation paths. [3] [4] [5]
