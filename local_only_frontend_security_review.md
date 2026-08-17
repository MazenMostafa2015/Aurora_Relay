# Aurora Relay Local-Only Frontend Security Review

**Review date:** 17 August 2026  
**Reviewer:** Manus AI  
**Disposition:** **Pass, with documented release gates**

## Scope and conclusion

This review covered the **desktop renderer and local-only fallback path**: the production frontend produced by Vite, the release sanitization step, the fallback HTML and JavaScript, Electron’s renderer-loading boundary, and the desktop backend’s loopback serving model. It did not assess user-configured model providers, MCP servers, or a release channel intentionally enabled for application updates.

The default desktop release path is now self-contained and local-only. The sanitizer removes platform-injected diagnostic markup, the dashboard no longer references Manus-hosted visual assets, and the production API client derives its endpoint from the renderer’s current loopback origin. The fallback page contains only a same-origin health check. The rendered application is restricted by a Content Security Policy that permits connections only to its own origin. [1] [2] [3]

> **Meaning of local-only in this review:** the fallback and packaged renderer may communicate with the bundled application service on `127.0.0.1`; they do not load third-party assets, transmit telemetry, or initiate remote renderer requests under the default configuration.

| Review area | Result | Evidence |
| --- | --- | --- |
| Platform diagnostics and runtime injection | Pass | Release sanitizer strips `debug-collector`, `manus-runtime`, and HTML comments before packaging. [1] |
| External and Manus-hosted frontend assets | Pass | Source and sanitized output scans found no `/manus-storage/`, `/__manus__/`, analytics, or diagnostic markers. |
| Content Security Policy | Pass | The release and fallback CSP specify `default-src 'self'` and `connect-src 'self'`. [1] [2] |
| Fallback request behavior | Pass | The only request is `fetch("/health")` with same-origin credentials. [3] |
| Dashboard API routing | Pass | Production defaults to `${window.location.origin}/api/v1`, which follows Electron’s randomized loopback port. [4] |
| Desktop backend exposure | Pass by code review | Electron selects a port on `127.0.0.1`, and the packaged backend receives that explicit loopback bind address. [5] |
| Automatic update traffic | Disabled by default | Update checks require `AURORA_UPDATE_FEED`; do not set it for a strictly local-only distribution. [6] |

## Remediation completed

The review identified two platform-specific release risks. First, the built HTML could contain a diagnostic collector and a large inline `manus-runtime` payload. Second, the dashboard’s decorative images were served from `/manus-storage/`, which would leave the packaged release dependent on an unavailable platform path. Both paths have been removed from the release output.

The sanitizer now removes the injected scripts and comments before it adds the restrictive CSP and rejects any remaining external or Manus-hosted `src` or `href` attribute. The visual treatment was rebuilt with CSS gradients and a native brand glyph, eliminating all source references to `/manus-storage/`. The production API client no longer defaults to a fixed `localhost:8000` port; it uses the current loopback origin in production, matching Electron’s dynamically selected backend port. [1] [4] [5]

| Former issue | Resolution | Security effect |
| --- | --- | --- |
| `/__manus__/debug-collector.js` injected in built HTML | Removed during release sanitization | Prevents diagnostic collection script from shipping in the desktop renderer. |
| `manus-runtime` inline payload injected in built HTML | Removed during release sanitization | Removes injected platform code and its embedded asset references. |
| `/manus-storage/` logo and background references | Replaced with CSS artwork and a native glyph | Removes hosted runtime asset requests and package visual breakage. |
| Fixed production API fallback (`localhost:8000`) | Changed to same-origin `/api/v1` | Keeps dashboard traffic on Electron’s randomized loopback port. |

## Validation evidence

The following checks completed in this environment.

| Command or check | Outcome | Notes |
| --- | --- | --- |
| Build frontend, copy output, and run `sanitize-frontend.mjs` | Pass | The sanitized `index.html` retained only local `/assets/...` JavaScript and CSS. |
| Recursive scan of source and sanitized release output | Pass | No `/manus-storage/`, `/__manus__/`, `debug-collector`, `manus-runtime`, analytics marker, or fixed-port production API URL was found. |
| Fallback syntax and static request scan | Pass | `desktop-fallback.js` parses and has one same-origin `/health` request; no remote URL, beacon, XHR, WebSocket, telemetry, or diagnostic marker was found. |
| Electron and desktop JavaScript parsing | Pass | `main.js`, `preload.js`, `setup-wizard.js`, `updater.js`, and the sanitizer parse successfully. |
| Backend pytest suite | Pass | **14 tests passed**. The current workspace contains 14 collected tests, not the 50 referenced by an earlier session summary. |
| Backend Python compilation | Pass | `compileall` completed without errors. |
| Frontend TypeScript check | Pass | `pnpm check` completed successfully. |
| Frontend production build | Pass | Vite and server bundle builds completed successfully. |
| Playwright E2E | Not executable | `pnpm test:e2e` correctly invoked Playwright but found no configuration or test files in this workspace, so it exited with “No tests found.” |

The build reports a non-blocking bundle-size advisory for the main JavaScript chunk. This is a performance-maintenance consideration, not a telemetry or local-only boundary failure.

## Operational boundary and remaining gates

The local-only renderer guarantee applies to the normal desktop frontend path. The Electron main process still includes controlled external capabilities that are dormant or user-mediated by default. The updater is disabled unless an operator provides `AURORA_UPDATE_FEED`; enabling it intentionally permits signed-update network traffic. The setup wizard may present official installation links, but opening them requires a user action. Separately, AI providers and MCP tools can make network requests only when an operator configures such integrations; that behavior is outside the fallback renderer’s scope.

| Gate | Why it remains | Required action before public release |
| --- | --- | --- |
| Native Windows build and installer execution | Cannot be produced or signed faithfully on this Linux workspace | Run the Windows release workflow on a protected Windows runner with signing credentials. |
| macOS notarization and clean-machine installation | Requires Apple credentials and a macOS host | Build, notarize, and test on an isolated macOS machine. |
| Linux installer smoke test | Requires a Docker-enabled or clean desktop environment | Install the AppImage or native package and verify launch, loopback binding, fallback handling, and uninstall behavior. |
| E2E test restoration | The repository has no Playwright configuration or test files | Restore the previously referenced suite or add a maintained Playwright project before promotion. |
| Strictly offline distribution | Update channel and configured providers can be intentional network paths | Leave `AURORA_UPDATE_FEED` unset and document/disable any configured remote provider or MCP integration. |

## Release recommendation

The local-only fallback implementation is approved for the **default desktop configuration** after the changes in this review. Promotion to a public native installer should remain conditional on native-platform signing and clean-machine checks, plus restoration of the absent E2E suite. A distribution that must remain offline should ship with no update-feed environment variable and no preconfigured remote provider or MCP endpoint.

## References

[1]: ../desktop/scripts/sanitize-frontend.mjs "Release frontend sanitizer"
[2]: templates/secure-desktop/index.html "Local-only fallback HTML and CSP"
[3]: templates/secure-desktop/assets/desktop-fallback.js "Fallback local health-check client"
[4]: ../frontend/client/src/lib/api.ts "Same-origin production API client"
[5]: ../desktop/electron/main.js "Electron loopback backend lifecycle"
[6]: ../desktop/electron/updater.js "Opt-in updater configuration"
