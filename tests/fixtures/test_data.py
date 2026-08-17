from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4


@dataclass(frozen=True)
class TestUser:
    username: str = "integration_user"
    email: str = "integration@example.com"
    password: str = "integration-pass-123"


@dataclass(frozen=True)
class TestTask:
    order: str = "List the files in the current workspace"


def unique_user(prefix: str = "integration") -> TestUser:
    suffix = uuid4().hex[:8]
    return TestUser(username=f"{prefix}_{suffix}", email=f"{prefix}_{suffix}@example.com")
