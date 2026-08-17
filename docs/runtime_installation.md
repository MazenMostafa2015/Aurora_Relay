# Aurora Relay Runtime Installation Guide

Aurora Relay is designed to work in a local-first mode, but two optional host runtimes provide important capabilities. **Ollama** supplies local model inference. **Docker** provides the isolated execution boundary required by the code-execution tools. The desktop application detects both during first run and records their availability in the local profile.

> Aurora Relay never runs untrusted code directly on the host. If Docker is missing, stopped, inaccessible, or unhealthy, code execution remains disabled rather than falling back to a host shell.

## Recommended installation strategy

Aurora Relay should not silently download or install either runtime. Both runtimes can require elevated privileges, virtualization, firewall changes, large model or image downloads, and separate license or organization-policy review. Instead, the setup wizard checks availability, explains the consequence of each missing runtime, opens the official installation guide, and offers a retry after the user completes installation.

| Runtime | Required for | Default policy | If unavailable |
| --- | --- | --- | --- |
| Ollama | Local model inference | Preferred, but optional | Local-model selection is disabled; configured cloud providers may still be used. |
| Docker Engine/Desktop | Sandboxed code execution | Required for execution tools | Code execution remains disabled; no host fallback is permitted. |

The installer itself remains small and reproducible. Runtime installation is a post-install onboarding step, which avoids embedding third-party installers, prevents unexpected privilege escalation, and makes enterprise software-distribution policies explicit.

## Ollama

Ollama is the preferred local inference path when users want prompts and results to remain on their machine. Users should install it from the official [Ollama download page][1]. The official page provides separate paths for macOS, Linux, and Windows; its current download page states that the macOS package requires macOS 14 Sonoma or later, while the Windows page states that Windows 10 or later is required.[1] [2]

After installation, launch Ollama if the platform does not start it automatically. Aurora Relay checks `ollama --version` during first run. A successful version response marks the local-model runtime as ready. The application does not pull a model automatically because model downloads can be large and model selection is a user decision. The next product step should be a model-picker screen that explains disk usage and allows the user to run an explicit `ollama pull <model>` action through a separately reviewed, user-confirmed flow.

If Ollama is not found, the setup window presents an **Install Ollama** link and allows the user to continue. Continuing does not erase the preference to prefer local inference; it records that local inference is currently unavailable and prevents the UI from presenting it as ready. After installation, the user can reopen Settings or rerun the setup check.

## Docker

Docker is the required isolation runtime for Aurora Relay’s code-execution tools. Docker Desktop is the simplest supported path for macOS, Windows, and users who prefer a managed graphical environment; Docker describes Desktop as an application for Mac, Linux, and Windows that includes the Docker Engine and CLI.[3] Linux operators who prefer a daemon-managed installation can use the official Docker Engine installation procedures for their distribution.[4]

The first-run probe executes `docker version` and requires a healthy server response, not merely the presence of a Docker CLI binary. This distinction catches the common state where Docker Desktop is installed but not running, the daemon is inaccessible, the current user lacks permission, or the Linux service has not started. On Linux, users should follow Docker’s official post-install guidance when configuring non-root access; membership in the `docker` group grants powerful control over the Docker daemon and must be treated as a privileged security decision.[5]

Aurora Relay does not automatically add users to groups, change daemon permissions, enable virtualization, or mount the host Docker socket into the application. The user or administrator must complete those actions through the operating system’s approved process. After Docker becomes healthy, the user can retry the check. Only then does the application enable the code-execution capability.

## First-run states and recovery

The setup wizard reports each phase independently. A green state means the runtime passed the health check. An amber state means the runtime is optional or unavailable and provides an installation link. A fatal probe error includes a technical detail panel, a retry action, and a safe continuation path. A missing Docker runtime is never treated as a recoverable permission to run code on the host.

| Message | Likely cause | User action |
| --- | --- | --- |
| “Ollama was not detected” | Ollama is not installed or is not on the executable path. | Install from the official page, start the service if needed, and retry. |
| “Docker is unavailable” | Docker Desktop/Engine is stopped, unhealthy, or inaccessible to the current user. | Start Docker, resolve permissions or virtualization requirements, and retry. |
| “Runtime checks failed unexpectedly” | A process probe timed out or returned an unexpected operating-system error. | Inspect technical details, verify endpoint security policy, and retry. |
| Backend unavailable | The packaged local API did not start. | Check application logs; do not bypass the local service or run the backend with a public bind address. |

## Enterprise and privacy guidance

Organizations should distribute Ollama and Docker through their normal endpoint-management systems when local installation is restricted. The Aurora Relay installer should be deployed separately from runtime packages, with runtime versions pinned and reviewed by the organization. Cloud-provider access remains opt-in, and first-run diagnostics are disabled by default. No prompts, task content, model outputs, API keys, or authorization headers should be included in diagnostics.

Docker licensing and commercial-use obligations depend on the selected Docker product and organization size. Review Docker’s current licensing language and subscription requirements before standardizing Docker Desktop for an enterprise fleet.[4] Ollama distribution, model licenses, and model-specific terms must likewise be reviewed before bundling or redistributing Ollama or model files. Aurora Relay therefore treats both runtimes as user- or administrator-installed dependencies rather than redistributing them in the application installer.

## References

[1]: https://ollama.com/download "Ollama download page"
[2]: https://ollama.com/download/windows "Ollama Windows download page"
[3]: https://docs.docker.com/desktop/ "Docker Desktop documentation"
[4]: https://docs.docker.com/engine/install/ "Docker Engine installation documentation"
[5]: https://docs.docker.com/engine/install/linux-postinstall/ "Docker Engine Linux post-installation documentation"
