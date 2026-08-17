"""Consistent MCP error handling and JSON-lines observability."""
from __future__ import annotations

import inspect
import json
import logging
import time
from collections.abc import Awaitable, Callable
from functools import wraps
from pathlib import Path
from typing import Any, TypeVar

from .protocol import error_result

T = TypeVar("T")


class MCPError(Exception):
    """Base class for expected MCP-facing errors."""

    code = "MCP_ERROR"


class ValidationError(MCPError):
    code = "INVALID_INPUT"


class PermissionDeniedError(MCPError):
    code = "PERMISSION_DENIED"


class ToolExecutionError(MCPError):
    code = "TOOL_EXECUTION_ERROR"


def configure_logging(log_path: str | Path | None = None) -> logging.Logger:
    """Configure stderr/file logging without contaminating stdio transport."""
    logger = logging.getLogger("mcp_servers")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler: logging.Handler = logging.FileHandler(log_path) if log_path else logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        logger.addHandler(handler)
    return logger


def _log_event(event: dict[str, Any], logger: logging.Logger) -> None:
    logger.info(json.dumps(event, default=str, sort_keys=True))


def handle_mcp_error(func: Callable[..., T] | Callable[..., Awaitable[T]]) -> Callable[..., Any]:
    """Wrap a tool so expected and unexpected errors become actionable MCP payloads."""
    logger = logging.getLogger("mcp_servers")
    is_async = inspect.iscoroutinefunction(func)

    @wraps(func)
    async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
        started = time.perf_counter()
        try:
            result = await func(*args, **kwargs)
            _log_event({"event": "tool_call", "tool": func.__name__, "success": True, "duration_ms": round((time.perf_counter() - started) * 1000, 2)}, logger)
            return result
        except MCPError as exc:
            _log_event({"event": "tool_call", "tool": func.__name__, "success": False, "code": exc.code, "duration_ms": round((time.perf_counter() - started) * 1000, 2)}, logger)
            raise
        except Exception as exc:  # defensive boundary for agent-facing tools
            logger.exception("Unexpected tool failure: %s", func.__name__)
            raise ToolExecutionError(f"Unexpected error while executing {func.__name__}: {exc}") from exc

    @wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        started = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            _log_event({"event": "tool_call", "tool": func.__name__, "success": True, "duration_ms": round((time.perf_counter() - started) * 1000, 2)}, logger)
            return result
        except MCPError as exc:
            _log_event({"event": "tool_call", "tool": func.__name__, "success": False, "code": exc.code, "duration_ms": round((time.perf_counter() - started) * 1000, 2)}, logger)
            raise
        except Exception as exc:
            logger.exception("Unexpected tool failure: %s", func.__name__)
            raise ToolExecutionError(f"Unexpected error while executing {func.__name__}: {exc}") from exc

    return async_wrapper if is_async else sync_wrapper
