# Secure Desktop Configuration Template

This package replaces the two release blockers found in the uploaded archive: the shipped development JWT secret and the malformed placeholder `index.html`. It is intended for the desktop build source tree, not as an in-place change to an already-installed application directory.

## Included Replacements

| Template | Replace in source tree | Purpose |
|---|---|---|
| `templates/secure-desktop/runtime_secrets.py` | `backend/runtime_secrets.py` | Generates and loads one strong per-user JWT secret before application settings import. |
| `templates/secure-desktop/run.py` | `backend/run.py` | Keeps data on the user profile, binds to loopback, and provisions the secret before importing FastAPI. |
| `templates/secure-desktop/settings.py` | `backend/app/config/settings.py` | Removes the default JWT value and working-directory `.env` loading. |
| `templates/secure-desktop/index.html` | Packaged fallback `frontend/index.html` | Provides valid local-only startup UI with a restrictive CSP. |
| `templates/secure-desktop/assets/desktop-fallback.js` | Packaged `frontend/assets/desktop-fallback.js` | Polls only same-origin `/health`, sends no telemetry, and reports a local failure state. |

## Integration Sequence

Copy `runtime_secrets.py` and the secure `run.py` into `backend/`. Copy the secure settings template into `backend/app/config/settings.py`. This order is important: `run.py` must call `load_runtime_secret()` before it imports a module that imports `app.config.settings`.

Copy the HTML and JavaScript fallback into the frontend directory selected by `AURORA_FRONTEND_DIR`. Ensure the packaged frontend has an `assets/` directory, because the backend only mounts static assets when that directory exists. Remove `public/__manus__/debug-collector.js`, `app.asar.bak*`, source backups, tests, caches, and build output from the release allowlist.

The fallback is not a replacement for the Aurora Relay React workspace. It is a valid, local-only diagnostic page. The Electron main process should normally load the validated production React build; this fallback exists only while the local backend and renderer are starting or when a real frontend bundle is unavailable.

## Windows ACL Requirement

On first launch, the template writes `%APPDATA%\\AuroraRelay\\config\\runtime.env` and invokes `icacls` to remove inherited permissions and grant full control only to the current Windows user. The backend fails closed when this protection cannot be applied. Review this behavior with enterprise desktop-management administrators before deployment, because managed profiles may use a different ACL policy.

The secret is never printed, never stored in the installed application directory, and never accepted from an unexpected environment override. Rotating the secret signs out existing local sessions; close Aurora Relay, remove the protected `runtime.env` file using an administrator-approved procedure, and restart the application.

## Required Build and Test Checks

Run Python syntax validation on `runtime_secrets.py`, `run.py`, and `settings.py`. Run the backend tests and package the frontend using the regular desktop build. On a clean Windows machine, verify that the first launch creates the protected secret, the local backend listens only on `127.0.0.1`, the Electron shell loads the real dashboard, the fallback contains no `__manus__` collector, and the installer passes Authenticode verification.

```powershell
Get-AuthenticodeSignature '.\Aurora Relay Setup <version>.exe' | Format-List
Get-FileHash '.\Aurora Relay Setup <version>.exe' -Algorithm SHA256
```

Finally, keep external LLM keys out of the package. Accept provider credentials only through explicit user-managed configuration or a centrally managed enterprise secret provider; do not add them to `runtime.env`.
