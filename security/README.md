# Security validation

Run the following checks from the repository root before release:

```bash
python -m compileall -q backend mcp_servers
bandit -r backend mcp_servers -c security/.bandit
pip-audit -r requirements.txt
cd frontend && pnpm audit --prod
```

The CI workflow also runs a filesystem vulnerability scan with Trivy. Treat **CRITICAL** findings as release blockers unless a documented exception has an owner, rationale, and expiry date.

Production controls include a non-root backend image, an unprivileged Nginx frontend, explicit CORS and trusted-host settings, JWT secret injection through the environment, rate limiting, security headers, disabled sandbox networking by default, no Docker socket mounted into the application containers, and health-gated service startup.

Before production, replace all development defaults, use a managed secret store, terminate TLS at the edge, restrict database and Redis network access, configure backups, rotate JWT signing secrets according to policy, and verify that sandbox execution is isolated on a separate worker boundary. The Phase 5 sandbox remains a high-risk capability; it should not be exposed to untrusted users without an operational review.
