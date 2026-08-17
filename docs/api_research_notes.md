# Phase 6 API Research Notes

The API design follows the official FastAPI patterns for dependency injection, OAuth2/JWT bearer security, WebSockets, middleware, and application lifecycle management. SQLAlchemy's asyncio documentation emphasizes that an `AsyncSession` is not safe to share across concurrent tasks, so the implementation should create one session per request or task. Pydantic Settings provides environment-driven configuration and is appropriate for secrets and deployment-specific values.

## Sources

1. FastAPI, **OAuth2 with Password (and hashing), Bearer with JWT tokens**: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
2. FastAPI, **WebSockets**: https://fastapi.tiangolo.com/advanced/websockets/
3. FastAPI, **FastAPI reference**: https://fastapi.tiangolo.com/reference/fastapi/
4. SQLAlchemy, **Asynchronous I/O**: https://docs.sqlalchemy.org/en/latest/orm/extensions/asyncio.html
5. SQLAlchemy, **Session Basics**: https://docs.sqlalchemy.org/en/latest/orm/session_basics.html
6. Pydantic, **Settings Management**: https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/

## Design implications

The API will use versioned `/api/v1` routes, typed Pydantic request and response models, dependency-injected services, request-scoped persistence, JWT access tokens with revocation support, authenticated WebSocket handshakes, in-memory rate limiting with a Redis-compatible abstraction, structured error responses, and a lifespan-managed application state. PostgreSQL and Redis are supported through configuration, while a SQLite and in-memory fallback keeps local tests and development deterministic when those services are unavailable.
