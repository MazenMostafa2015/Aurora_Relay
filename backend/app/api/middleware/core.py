from __future__ import annotations

import time
import uuid
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimiter:
    def __init__(self): self.requests = defaultdict(deque)
    def allow(self, key: str, limit: int, window: int) -> tuple[bool, int]:
        now = time.monotonic(); q = self.requests[key]
        while q and q[0] <= now - window: q.popleft()
        if len(q) >= limit: return False, 0
        q.append(now); return True, limit - len(q)


class RequestMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limiter: RateLimiter, limit: int, window: int):
        super().__init__(app); self.limiter, self.limit, self.window = limiter, limit, window
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        allowed, remaining = self.limiter.allow(f"{request.client.host if request.client else 'unknown'}:{request.url.path}", self.limit, self.window)
        if not allowed: return JSONResponse(status_code=429, content={"code": 429, "message": "Too many requests", "request_id": request_id}, headers={"x-request-id": request_id})
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["x-request-id"] = request_id; response.headers["x-rate-limit-remaining"] = str(remaining); response.headers["x-response-time"] = f"{time.perf_counter()-started:.4f}s"
        return response
