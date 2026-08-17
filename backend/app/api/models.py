from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserRegister(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$")
    email: EmailStr
    password: str = Field(min_length=8, max_length=256)


class UserLogin(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    username: str
    email: EmailStr
    created_at: datetime
    updated_at: datetime | None = None
    is_active: bool
    is_admin: bool


class TaskStatus(str, Enum):
    CREATED = "created"
    PLANNING = "planning"
    PLANNED = "planned"
    EXECUTING = "executing"
    PAUSED = "paused"
    WAITING_FOR_INPUT = "waiting_for_input"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WAITING_APPROVAL = "waiting_approval"


class TaskCreate(BaseModel):
    order: str = Field(min_length=1, max_length=20000)
    context: dict[str, Any] = Field(default_factory=dict)
    start_immediately: bool = True


class TaskUpdate(BaseModel):
    status: TaskStatus | None = None
    context: dict[str, Any] | None = None


class StepResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    task_id: str
    description: str
    order: int
    status: StepStatus
    tools_required: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    output_data: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    requires_approval: bool = False
    approval_given: bool = False


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    user_id: str
    order: str
    status: TaskStatus
    steps: list[StepResponse] = Field(default_factory=list)
    current_step_index: int = 0
    summary: str | None = None
    final_output: dict[str, Any] | None = None
    error: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    progress: float = 0.0
    created_at: datetime
    updated_at: datetime | None = None
    completed_at: datetime | None = None
    estimated_complexity: str = "moderate"


class TaskListResponse(BaseModel):
    tasks: list[TaskResponse]
    total: int
    page: int
    limit: int


class ToolResponse(BaseModel):
    name: str
    description: str = ""
    server: str = "unknown"
    schema: dict[str, Any] = Field(default_factory=dict)


class ToolListResponse(BaseModel):
    tools: list[ToolResponse]
    count: int


class WSMessage(BaseModel):
    type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ErrorResponse(BaseModel):
    code: int
    message: str
    details: dict[str, Any] | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    request_id: str | None = None


class HealthResponse(BaseModel):
    status: str
    services: dict[str, Any]
    version: str


class AdminStatsResponse(BaseModel):
    users: int
    tasks: int
    active_sessions: int
    audit_events: int
