# Aurora Relay Final Operations and Contributor Guide

## Local-first operating model

Aurora Relay is designed to remain useful when no external service is reachable. The renderer ships with local fallbacks and the offline guard rejects non-packaged renderer references. Docker remains the only permitted execution boundary for extensions; a package that is unsigned, altered, untrusted, revoked, or unavailable for verification cannot be installed, enabled, or run.

## Developer quick start

Run the backend tests from the repository root with `python3 -m pytest backend/tests -q`. In `frontend`, run `pnpm validate` for TypeScript, production build, and offline-asset checks. Run `pnpm test:e2e` for browser interactions and `pnpm test:visual` for visual baselines. The deterministic reference generator is `python3 scripts/generate_docs.py`; generated documents must be committed when they change.

## Extension author workflow

Only build packages through `scripts/sign_extension.py`. Generate signing material outside the repository, keep private keys outside source control, publish a bootstrap-signed keyring, then sign each `.aurx` archive. Each package binds an RFC 8785 canonical manifest and every declared payload hash. Operators see safe verification evidence only; private keys and credential plaintext never cross the renderer boundary.

## Operator recovery

When connector work fails, read the displayed recovery guidance before retrying. Connector requests time out deterministically and retry only bounded transient failures. Sensitive tests, actions, Revit previews, and Revit applies are owner-scoped and locally rate-limited. Connector credentials stay encrypted in the native vault and security-sensitive operations are represented in the local audit history.

## Maintenance checklist

Select health history retention through the authenticated operations API with 7-, 30-, or 90-day periods. Review extension trust status before enabling any package. Before merging a change, run the backend suite, `pnpm validate`, interaction tests, visual tests when relevant, and the deterministic documentation generator. Do not create releases or deployments from routine maintenance commits.
