# Phase 8 Integration, Testing & Deployment Preparation

## Discovery and prerequisites
- [ ] Read the full Phase 8 specification and extract all required deliverables.
- [ ] Inventory the existing backend, frontend, Docker, test, and documentation files.
- [ ] Check availability of Docker, PostgreSQL, Redis, Node.js, Python, Playwright, and load/security tooling.
- [ ] Document environment limitations and distinguish executable validation from configuration-only validation.

## Integration and end-to-end testing
- [ ] Add reusable integration fixtures and mock responses.
- [ ] Add API integration coverage for health, auth, tasks, tools, and WebSocket behavior.
- [ ] Add agent, sandbox, and MCP integration coverage with safe fakes.
- [ ] Add full workflow and scenario tests.
- [ ] Add frontend Playwright configuration and realistic UI workflow specs.
- [ ] Add frontend test selectors only where needed without compromising the current design.

## Performance and security
- [ ] Add load-test scenarios for health, auth, task creation, and tool discovery.
- [ ] Add stress-test documentation and measurable acceptance thresholds.
- [ ] Add dependency and static security scanning configuration.
- [ ] Review secrets, CORS, host validation, rate limits, sandbox socket exposure, and production defaults.
- [ ] Document known limitations and operator response steps.

## Deployment and operations
- [ ] Add full-stack Docker Compose with database, Redis, backend, frontend, reverse proxy, monitoring, and logging profiles.
- [ ] Add backend and frontend production Dockerfiles and environment templates.
- [ ] Add reverse-proxy configuration and health checks.
- [ ] Add Prometheus/Grafana configuration and application metrics guidance.
- [ ] Add structured logging and log shipping configuration or a documented safe baseline.
- [ ] Add CI workflow for lint, type checks, unit/integration tests, builds, and security checks.

## Documentation and final validation
- [ ] Write deployment, user, developer, and production-readiness documentation.
- [ ] Run all available tests, compilation checks, builds, compose config validation, and smoke tests.
- [ ] Record limitations, skipped checks, and required production follow-up.
- [ ] Update the checklist with completed items and attach final deliverables.

## Desktop packaging workstream

- [x] Create a secure Electron shell with isolated renderer, preload IPC, local backend lifecycle, tray behavior, and graceful shutdown.
- [x] Add a packaged backend entry point with per-user data/config/log directories and SQLite defaults.
- [x] Add PyInstaller and Electron Builder configuration for Windows, macOS, and Linux artifacts.
- [x] Add first-run setup and updater foundations without enabling unsafe renderer privileges.
- [x] Add cross-platform build scripts, signing placeholders, checksums, and release documentation.
- [x] Validate JavaScript syntax, Python compilation, frontend build, and desktop configuration.
- [x] Record platform-specific limitations: cross-compilation, Ollama distribution/licensing, Docker sandbox availability, code signing, notarization, and update signing.

## Ollama and Docker onboarding workstream

- [x] Document supported Ollama and Docker installation paths, permissions, privacy, licensing, and fail-closed behavior for end users.
- [x] Add first-run runtime detection and staged progress reporting for Ollama and Docker.
- [x] Add detailed setup error states with actionable recovery, retry, skip, and diagnostics options.
- [x] Preserve local-first defaults and never execute code on the host when Docker is unavailable.
- [x] Validate setup-window syntax, backend regression tests, frontend checks, and desktop build metadata.

## Desktop archive delivery

- [x] Assemble a clean desktop source archive without build caches, node_modules, generated databases, logs, workspace artifacts, or secrets.
- [x] Include the Electron shell, packaged-backend configuration, installer wrappers, resources, build script, and runtime documentation.
- [x] Validate ZIP listing, archive extraction, JavaScript/Python metadata, and checksum generation.
- [x] Deliver the ZIP and state clearly that it is a source/build package, not a native signed installer.

## Native installer guide and architecture deck

- [x] Read the desktop build metadata, architecture notes, and runtime integration documentation.
- [x] Draft platform-specific Windows, macOS, and Linux native-installer build instructions with signing and release gates.
- [x] Prepare slide content covering system architecture, desktop lifecycle, MCP/agent flow, Ollama, Docker, security, and release strategy.
- [x] Generate and validate the presentation deck.
- [x] Deliver the build guide and presentation artifacts.

## Single-file Windows deployment request

- [x] Verify what `.SP1` means in the requested deployment context and whether it is a supported installer artifact.
- [x] Decide whether to deliver an SP1-compatible package or a supported single-file Windows bootstrapper instead.
- [x] Define prerequisite installation boundaries for Node/Python/Electron, Ollama, Docker Desktop, and application files.
- [x] Implement or document the supported Windows deployment path with elevation, consent, logging, rollback, and fail-closed behavior.
- [x] Validate package configuration and explain why native signing and Windows CI are required for a production installer.

## Windows CI/CD and presentation script

- [x] Review the current Windows packaging metadata, bootstrapper, signing hooks, and release docs.
- [x] Design the Windows CI/CD stages for build, test, signing, checksum, provenance, and promotion.
- [x] Add a GitHub Actions workflow template and CI/CD operator documentation without embedding secrets.
- [x] Generate speaker notes explaining the prerequisite bootstrapper and deployment workflow.
- [x] Validate workflow YAML, package metadata, scripts, and speaker notes; report native release prerequisites.

## Reusable MCP application builder skill

- [x] Define triggers and scope for building full-stack MCP AI applications with desktop packaging and runtime onboarding.
- [x] Plan concise SKILL.md navigation and progressive reference files for backend, frontend, sandbox, desktop, Ollama/Docker, CI/CD, testing, and presentations.
- [x] Update the existing mcp-ai-application-builder skill using the skill-creator workflow without duplicating project documentation.
- [x] Validate the skill package and deliver its SKILL.md so Manus can package it as a downloadable `.skill` file.

## Skill refresh delivery

- [x] Re-read and assess the existing mcp-ai-application-builder skill and references.
- [x] Refresh the skill only where the completed workflow adds reusable guidance.
- [x] Run quick_validate.py and deliver the skill entry point for packaging.

## Attached content follow-up

- [x] Inspect pasted_content_10.txt and extract actionable requirements.
- [x] Map the requirements to the application, desktop package, documentation, or reusable skill.
- [x] Implement applicable changes and update relevant deliverables.
- [x] Validate the updated baseline and deliver the resulting artifacts.

## One-click installer stakeholder script

- [x] Review the existing architecture deck and one-click installer strategy.
- [x] Regenerate speaker notes with stakeholder framing and packaging-boundary explanations.
- [x] Present the deck with the updated notes and deliver the script artifact.

## Uploaded AuroraRelay installer review

- [x] Inspect archive structure and contents without executing untrusted files.
- [x] Assess installer metadata, bundled components, secrets exposure, and runtime boundaries.
- [x] Validate archive integrity and report remediation steps or release blockers.

## Secure desktop configuration templates

- [x] Review the installed-package settings, launcher, and fallback frontend behavior.
- [x] Create a per-install JWT provisioning template that fails closed rather than using a shipped default.
- [x] Create a valid local-only frontend fallback without development diagnostics or telemetry collectors.
- [x] Document integration, Windows ACL hardening, and validation steps.
- [x] Validate the template syntax and deliver the replacement package.

## Secure Windows installer build

- [ ] Inspect the clean release source, packaging configuration, and current build prerequisites.
- [ ] Stage the secure settings, launcher, and frontend fallback in a reproducible release workspace.
- [ ] Attempt Windows NSIS packaging and capture any generated setup artifact.
- [ ] Verify release contents, integrity, and platform/signing constraints.
- [ ] Deliver the installer or a Windows CI handoff if native packaging is unavailable.
