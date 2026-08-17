"""Retry helpers for transient MCP failures."""
from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Type

from .protocol import ConnectionError, ConnectionTimeoutError

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RetryConfig:
    max_retries: int = 2
    base_delay: float = 0.25
    max_delay: float = 5.0
    jitter: float = 0.1


async def retry_with_backoff(
    operation: Callable[[], Awaitable[Any]],
    config: RetryConfig | None = None,
    retryable_exceptions: tuple[Type[BaseException], ...] = (ConnectionError, ConnectionTimeoutError, TimeoutError, OSError),
) -> Any:
    """Run an async operation, retrying only configured transient failures."""
    policy = config or RetryConfig()
    last_error: BaseException | None = None
    for attempt in range(policy.max_retries + 1):
        try:
            return await operation()
        except retryable_exceptions as exc:
            last_error = exc
            if attempt >= policy.max_retries:
                break
            delay = min(policy.base_delay * (2**attempt), policy.max_delay)
            delay += random.uniform(0, max(policy.jitter, 0))
            logger.warning("Retrying MCP operation (%d/%d) in %.2fs: %s", attempt + 1, policy.max_retries, delay, exc)
            await asyncio.sleep(delay)
    assert last_error is not None
    raise last_error
