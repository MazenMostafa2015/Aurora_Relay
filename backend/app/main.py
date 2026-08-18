from __future__ import annotations

from contextlib import asynccontextmanager
import os
from pathlib import Path

from time import perf_counter

from fastapi import FastAPI, Response, WebSocket
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from .api.middleware.core import RateLimiter, RequestMiddleware
from .api.routes import admin, agent_loops, auth, connectors, tasks, tools
from .api.websocket.handlers import manager
from .config.settings import settings
from .database.session import SessionLocal, init_db
from .observability.metrics import log_event, metrics


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    app.state.services = {"mcp_client": None, "llm_manager": None, "coordinator": None}
    yield


app = FastAPI(title=settings.app_name, version=settings.app_version, description="REST and WebSocket API for the MCP AI agent application", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
if settings.allowed_hosts and settings.allowed_hosts != ["*"]:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
app.add_middleware(RequestMiddleware, limiter=RateLimiter(), limit=settings.rate_limit_requests, window=settings.rate_limit_window)
app.include_router(auth.router, prefix=settings.api_v1_str)
app.include_router(tasks.router, prefix=settings.api_v1_str)
app.include_router(tools.router, prefix=settings.api_v1_str)
app.include_router(connectors.router, prefix=settings.api_v1_str)
app.include_router(agent_loops.router, prefix=settings.api_v1_str)
app.include_router(admin.router, prefix=settings.api_v1_str)

@app.get("/", tags=["System"])
async def root():
    frontend_dir = Path(os.environ.get("AURORA_FRONTEND_DIR", ""))
    index_file = frontend_dir / "index.html"
    if index_file.is_file():
        return FileResponse(index_file)
    return {"name": settings.app_name, "version": settings.app_version, "docs": "/docs", "health": "/health"}

@app.get("/health", tags=["System"])
async def health(): return {"status": "healthy", "version": settings.app_version, "services": {"database": "configured", "redis": bool(settings.redis_url), "mcp": False, "llm": False, "coordinator": False}}

frontend_dir_value = os.environ.get("AURORA_FRONTEND_DIR")
frontend_dir = Path(frontend_dir_value).expanduser().resolve() if frontend_dir_value else None
if frontend_dir and frontend_dir.is_dir() and (frontend_dir / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=frontend_dir / "assets"), name="desktop-assets")

    @app.get("/{path:path}", include_in_schema=False)
    async def desktop_frontend(path: str):
        if path == "metrics":
            return await metrics_endpoint()
        candidate = (frontend_dir / path).resolve()
        if candidate.is_file() and frontend_dir in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(frontend_dir / "index.html")


@app.get("/metrics", tags=["System"], include_in_schema=False)
async def metrics_endpoint():
    return Response(content=metrics.prometheus(), media_type="text/plain; version=0.0.4")

@app.middleware("http")
async def observability_middleware(request, call_next):
    started = perf_counter()
    response = await call_next(request)
    duration = perf_counter() - started
    metrics.observe_request(request.method, request.url.path, response.status_code, duration)
    log_event("http_request", method=request.method, path=request.url.path, status=response.status_code, duration_ms=round(duration * 1000, 2))
    return response

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    db = SessionLocal()
    try: await manager.handle(websocket, db)
    finally: db.close()
