# One-click installer strategy

## Executive decision

The attachment describes a single-download experience for Windows, macOS, and Linux. That user experience is achievable as a **guided bootstrapper plus native application installer**, but not as one identical, fully offline executable that silently bundles and installs every third-party runtime on every platform.

Aurora Relay should package the application itself as a native Electron artifact containing the React frontend and frozen FastAPI/MCP backend. Python and Node.js are build-time dependencies and should not be required on the end user’s machine. Ollama and Docker remain separately governed runtime dependencies: Ollama is optional for local inference, while Docker is required for sandboxed code execution. Their installation must be explicit, license-aware, platform-specific, and observable. The application must remain fail-closed when Docker is unavailable.

## Requirement disposition

| Attachment requirement | Decision | Rationale |
|---|---|---|
| One downloadable application installer | Supported | Electron Builder produces native Windows, macOS, and Linux artifacts. |
| Bundle Python and Node.js | Supported through frozen backend and packaged frontend | End users do not need Python or Node installed. Avoid shipping unused development runtimes. |
| Bundle Ollama silently | Not supported by default | Vendor distribution, licensing, platform behavior, model size, updates, and permissions require separate policy and consent. |
| Bundle Docker Desktop silently | Not supported | Docker Desktop has separate licensing and privileged service requirements; it cannot be treated as an ordinary application file. |
| Include AI models in the installer | Optional, not default | Models are large, hardware-dependent, versioned, and may have separate licenses. Prefer an opt-in download with disk-space checks. |
| Work completely offline | Partially supported | The packaged application can start offline; first-time runtime/model installation and cloud providers require network access unless pre-provisioned by an administrator. |
| No manual steps | Supported only for the application install | Runtime installation, administrator approval, licenses, reboots, and model selection may require explicit user action. |
| Desktop shortcut, tray, startup | Supported as opt-in installer tasks | Defaults must respect user choice and operating-system startup policies. |
| One identical installer across platforms | Not supported | Windows NSIS, macOS DMG/PKG, and Linux AppImage/DEB have different signing, permissions, service, and update models. |

## Recommended user journey

The user downloads the platform-native Aurora Relay installer and launches it. The installer installs the signed application and offers clearly labeled runtime choices. After launch, the first-run setup window probes Ollama and Docker independently, displays progress and diagnostics, and provides official installation links or organization-approved package sources. The user may continue without Ollama, which disables local-model readiness, but cannot enable sandboxed code execution until Docker passes its health check.

If an organization wants a no-interaction deployment, it should use endpoint-management tooling such as Intune, Jamf, or an approved Linux configuration system to preinstall and configure the third-party runtimes. Aurora Relay can then detect those installations at first launch. This separates application delivery from privileged system-runtime governance.

## Packaging boundaries

The application installer should contain the Electron shell, frontend build, frozen backend executable, MCP server resources, default non-secret configuration, icons, and migration/bootstrap code. It should not contain production secrets, mutable databases, user logs, Docker socket credentials, or a host-execution fallback.

The bootstrapper may coordinate installation of approved runtime packages, but it must show the package identity, vendor, license links, requested privileges, download source, disk impact, and restart behavior before proceeding. It must use official vendor channels or enterprise mirrors, verify signatures or checksums where available, and record only non-sensitive package outcomes.

## Model strategy

Do not place large language models in the default installer. Offer an opt-in model setup step after Ollama is healthy. Check free disk space, architecture, expected download size, model license, and cancellation behavior before starting. Store model state in the user’s application data path and allow the user to remove or change models without reinstalling the application.

## Release and security gates

A production release requires native builds, platform signing, clean-machine installation, upgrade and uninstall tests, first-run tests with missing and stopped runtimes, offline startup tests, checksum verification, and a review of third-party licensing. The release notes must distinguish bundled application components from externally managed runtimes. An unsigned or partially verified bootstrapper must not be presented as a production installer.

## Conclusion

The safe interpretation of “one-click” is **one application download with a guided, consent-based runtime setup**, not silent redistribution of Docker, Ollama, and large model files. This preserves the polished onboarding goal while respecting security, licensing, platform, and operational constraints.
