from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

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


class ConnectorProvider(str, Enum):
    GITHUB = "github"
    REVIT = "revit"


class ConnectorStatus(str, Enum):
    NOT_CONFIGURED = "not_configured"
    TESTING = "testing"
    CONNECTED = "connected"
    NEEDS_ATTENTION = "needs_attention"
    DISABLED = "disabled"


def _safe_connector_configuration(value: dict[str, Any]) -> dict[str, Any]:
    blocked = {"token", "secret", "password", "authorization", "api_key", "credential"}
    for key in value:
        if key.lower().replace("-", "_") in blocked:
            raise ValueError("Connector credentials must be provided through the credential field, not configuration")
    return value


class ConnectorCreate(BaseModel):
    provider: ConnectorProvider
    display_name: str = Field(min_length=2, max_length=120)
    configuration: dict[str, Any] = Field(default_factory=dict)
    credential: str | None = Field(default=None, min_length=8, max_length=4096, repr=False)
    credential_label: str = Field(default="Primary credential", min_length=2, max_length=120)

    @field_validator("configuration")
    @classmethod
    def validate_configuration(cls, value: dict[str, Any]) -> dict[str, Any]:
        return _safe_connector_configuration(value)


class ConnectorUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=2, max_length=120)
    configuration: dict[str, Any] | None = None
    credential: str | None = Field(default=None, min_length=8, max_length=4096, repr=False)
    credential_label: str | None = Field(default=None, min_length=2, max_length=120)
    enabled: bool | None = None
    sort_order: int | None = Field(default=None, ge=1, le=10_000)

    @field_validator("configuration")
    @classmethod
    def validate_configuration(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        return _safe_connector_configuration(value) if value is not None else value


class ConnectorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    provider: ConnectorProvider
    display_name: str
    status: ConnectorStatus
    sort_order: int
    configuration: dict[str, Any] = Field(default_factory=dict)
    credential_configured: bool = False
    capabilities: list[str] = Field(default_factory=list)
    last_tested_at: datetime | None = None
    last_error: str | None = None
    created_at: datetime
    updated_at: datetime | None = None


class ConnectorListResponse(BaseModel):
    connectors: list[ConnectorResponse]
    count: int


class ConnectorActionRequest(BaseModel):
    action: str = Field(min_length=3, max_length=64, pattern=r"^[a-z_]+$")
    input: dict[str, Any] = Field(default_factory=dict)


class ConnectorActionResponse(BaseModel):
    ok: bool
    provider: ConnectorProvider
    action: str
    message: str
    data: dict[str, Any] = Field(default_factory=dict)


class RevitSetParameterInput(BaseModel):
    element_id: int = Field(gt=0)
    parameter: str = Field(min_length=1, max_length=120)
    value: str | int | float | bool


class RevitPlaceFamilyInput(BaseModel):
    family_symbol: str = Field(min_length=1, max_length=180)
    level: str = Field(min_length=1, max_length=120)
    x: float = Field(ge=-1_000_000, le=1_000_000)
    y: float = Field(ge=-1_000_000, le=1_000_000)
    z: float = Field(default=0, ge=-1_000_000, le=1_000_000)
    parameters: dict[str, str | int | float | bool] = Field(default_factory=dict)


class RevitPlanRequest(BaseModel):
    operation: Literal["set_parameter", "place_family_instance"]
    transaction_name: str = Field(min_length=3, max_length=120)
    set_parameter: RevitSetParameterInput | None = None
    place_family_instance: RevitPlaceFamilyInput | None = None

    @field_validator("set_parameter")
    @classmethod
    def validate_set_parameter(cls, value: RevitSetParameterInput | None, info: Any) -> RevitSetParameterInput | None:
        if info.data.get("operation") == "set_parameter" and value is None:
            raise ValueError("set_parameter payload is required for a set_parameter operation")
        return value

    @field_validator("place_family_instance")
    @classmethod
    def validate_place_family_instance(cls, value: RevitPlaceFamilyInput | None, info: Any) -> RevitPlaceFamilyInput | None:
        if info.data.get("operation") == "place_family_instance" and value is None:
            raise ValueError("place_family_instance payload is required for a place_family_instance operation")
        return value


class RevitPlanResponse(BaseModel):
    operation_id: str
    state: Literal["planned"]
    requires_confirmation: bool = True
    preview: dict[str, Any]
    message: str


class RevitApplyRequest(BaseModel):
    confirmation: Literal["APPLY"]


class RevitOperationResponse(BaseModel):
    operation_id: str
    state: Literal["applied", "failed", "rejected"]
    message: str
    result: dict[str, Any] = Field(default_factory=dict)
