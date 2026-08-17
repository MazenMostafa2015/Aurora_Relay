# Deployment Guide

## Local production-like stack

Copy `.env.example` to `.env`, replace every development secret, and start the stack:

```bash
cp .env.example .env
docker compose config
docker compose up --build -d
curl http://localhost:8080/healthz
curl http://localhost:8080/api/v1/health
```

The frontend is available at `http://localhost:8080`, Prometheus at `http://localhost:9090`, and Grafana at `http://localhost:3001`. The backend is intentionally not published directly by the Compose stack; the frontend Nginx container proxies `/api/` and `/ws`.

## Production requirements

Use a managed PostgreSQL instance, a managed Redis instance, an external secret manager, TLS termination, a private container registry, and a separate worker boundary for sandbox execution. Set explicit `CORS_ORIGINS` and `ALLOWED_HOSTS`; never use `*` in production. Use a random JWT signing key with an established rotation process. Disable public Grafana access or place it behind SSO and an internal network.

Run database migrations before making the new backend revision available. The current repository contains the initial Alembic entry point; production migration automation must be completed against the actual database URL and reviewed before destructive schema changes.

## Release and rollback

Build immutable images from a tagged commit, run the CI workflow, validate `docker compose config`, run the smoke checks, and deploy with a rolling strategy. Keep the previous image tag available. If health checks fail, stop promotion and roll back the backend and frontend image tags together. Do not run destructive database commands during rollback; restore data from the most recent verified backup only through the database operator process.

## Observability

Prometheus scrapes `/metrics`. Grafana is pre-provisioned with an overview dashboard for request volume, duration, task acceptance, and server errors. Application logs are JSON lines on stdout and should be collected by the platform log driver. Alert on sustained 5xx responses, health-check failures, elevated p95 latency, database connection errors, Redis failures, and sandbox audit events.

## Troubleshooting

If the backend is unhealthy, inspect `docker compose logs backend`, then check PostgreSQL and Redis health. If the frontend loads but API calls fail, verify the Nginx proxy target and backend health. If WebSocket updates fail, verify that the reverse proxy preserves HTTP/1.1 upgrade headers. If local Ollama is required, configure `OLLAMA_BASE_URL` for the container network and confirm the model is available to the daemon.
