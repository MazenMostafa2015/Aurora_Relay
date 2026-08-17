# Developer Guide

## Repository map

The Python backend lives in `backend/app`, the original MCP servers live in `mcp_servers`, the frontend lives in `frontend`, and deployment/observability assets live in `docker`, `monitoring`, and `security`. Phase-specific architecture documents are in `docs`.

## Local development

Use Python 3.12 or newer, Node 22, pnpm, and Docker for the full stack. For backend-only work:

```bash
pip install -r requirements.txt
PYTHONPATH=backend uvicorn backend.app.main:app --reload --port 8000
```

For frontend work:

```bash
cd frontend
pnpm install
pnpm dev
```

The frontend currently has local-first seeded state and typed API/WebSocket adapters. It does not contain credentials or direct access to MCP tools. Connect it to the Phase 6 API through the configured proxy before enabling live authenticated workflows.

## Validation commands

```bash
PYTHONPATH=backend pytest -q tests backend/tests
python -m compileall -q backend mcp_servers
cd frontend && pnpm validate
cd frontend && pnpm exec playwright install chromium && pnpm test:e2e
```

The test suite is designed to run with SQLite and deterministic fakes when PostgreSQL, Redis, Ollama, Docker, and external MCP daemons are unavailable. Live-service tests should be opt-in and clearly marked.

## Extending MCP and agents

Add a server under `mcp_servers` or `backend/app/core/mcp_servers`, register it in configuration, and cover discovery, allowlists, protocol-facing errors, and shutdown. Agent steps should remain dependency-aware and serializable. Sensitive operations must pass through the HITL approval layer. Sandbox execution must remain fail-closed and must never receive the host Docker socket from the application frontend.

## API conventions

Use `/api/v1`, typed Pydantic models, authenticated dependencies for protected routes, stable error envelopes, request IDs, and explicit status transitions. Add an integration test for every new route and update OpenAPI-facing documentation. Do not commit secrets, production database URLs, or generated runtime state.
