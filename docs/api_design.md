# Phase 6 API Design

The Phase 6 backend exposes a versioned FastAPI application at `/api/v1` and a WebSocket endpoint at `/ws`. The API uses Pydantic models for validation, request-scoped SQLAlchemy sessions, JWT bearer authentication with revocable sessions, and application lifespan state for MCP, LLM, and Coordinator components. FastAPI’s dependency injection and lifecycle patterns are used to keep route handlers thin and testable [1] [2].

| Area | Decision |
| --- | --- |
| Authentication | Short-lived JWT access tokens, bcrypt password hashes, hashed session tokens, logout and refresh revocation |
| Persistence | PostgreSQL-ready SQLAlchemy models with SQLite local fallback; one session per request |
| Real-time updates | Authenticated WebSocket handshake using bearer header or query token; per-user and per-task subscriptions |
| Rate limiting | In-memory sliding-window limiter for local use, with a Redis-compatible replacement point for multi-instance deployments |
| Errors | JSON responses containing code, message, request ID, and optional details |
| Versioning | Stable `/api/v1` route prefix; root and health endpoints remain unversioned |

## Authentication strategy

Registration validates username, email, and password constraints. Login verifies a bcrypt hash, creates a signed JWT, and persists only a SHA-256 token hash in the session table. Every protected request verifies both the JWT and its active, unexpired session record. Logout revokes the session; refresh revokes the old token before issuing a replacement. JWT secrets must be supplied through environment configuration in production.

## Rate limiting and operations

The local limiter keys requests by client address and route, removes timestamps outside the active window, and returns HTTP 429 with a request ID when exhausted. For multiple API workers, the same interface should be backed by Redis so limits are shared. Middleware also emits request IDs, response timing, and remaining quota headers.

## Error philosophy

Validation errors remain FastAPI-native, while application errors use stable HTTP status codes and structured JSON. Internal exception details are not exposed in production. Request IDs allow correlation across API logs, task events, audit logs, and downstream MCP/LLM calls.

## References

[1]: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/ "FastAPI OAuth2 and JWT"
[2]: https://fastapi.tiangolo.com/advanced/websockets/ "FastAPI WebSockets"
[3]: https://docs.sqlalchemy.org/en/latest/orm/extensions/asyncio.html "SQLAlchemy AsyncIO"
[4]: https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/ "Pydantic Settings"
