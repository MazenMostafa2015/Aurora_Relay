from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


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


class OperationalSystemHealth(BaseModel):
    status: Literal["operational", "degraded", "critical"]
    version: str
    uptime_seconds: int
    last_loop_completion: datetime | None = None
    metrics: dict[str, float] | None = None


class OperationalConnectorHealth(BaseModel):
    id: str
    provider: str
    display_name: str
    status: Literal["connected", "warning", "error", "disabled"]
    last_connected: datetime | None = None
    response_time_ms: int | None = None
    error: str | None = None
    credential_configured: bool


class OperationalLoopIterationHealth(BaseModel):
    iteration: int
    timestamp: datetime | None = None
    result: Literal["success", "failed", "partial"]
    summary: str


class OperationalAgentLoopHealth(BaseModel):
    state: Literal["idle", "running", "paused", "stopped"]
    current_iteration: int
    total_iterations: int
    last_result: Literal["success", "failed", "partial"] | None = None
    next_run: datetime | None = None
    recent_iterations: list[OperationalLoopIterationHealth] = Field(default_factory=list)


class OperationalReleaseHealth(BaseModel):
    version: str
    sha256_verified: bool
    provenance_verified: bool
    signer_pinned: bool
    timestamp_present: bool
    clean_machine_verified: bool
    trust_note: str


class OperationalVaultHealth(BaseModel):
    state: Literal["ready", "locked"]
    backend: str
    fallback: bool
    message: str


class OperationalActivity(BaseModel):
    id: str
    type: Literal["info", "success", "warning", "error"]
    message: str
    timestamp: datetime
    source: str


class OperationalAlert(BaseModel):
    id: str
    severity: Literal["warning", "error"]
    message: str
    recommendation: str | None = None


class OperationsHealthResponse(BaseModel):
    generated_at: datetime
    system: OperationalSystemHealth
    connectors: list[OperationalConnectorHealth] = Field(default_factory=list)
    agent_loop: OperationalAgentLoopHealth
    release: OperationalReleaseHealth
    vault: OperationalVaultHealth
    activities: list[OperationalActivity] = Field(default_factory=list)
    alerts: list[OperationalAlert] = Field(default_factory=list)


class ExtensionKind(str, Enum):
    DASHBOARD_PANEL = "dashboard_panel"
    SANDBOXED_TOOL = "sandboxed_tool"
    CONNECTOR_ADAPTER = "connector_adapter"


class ExtensionPermission(str, Enum):
    SANDBOX_EXECUTE = "sandbox.execute"
    CONNECTOR_READ = "connector.read"
    AGENT_READ = "agent.read"


class ExtensionSignatureStatus(str, Enum):
    VERIFIED = "verified"
    UNSIGNED = "unsigned"
    TAMPERED = "tampered"
    UNTRUSTED = "untrusted"
    REVOKED = "revoked"
    INVALID = "invalid"
    TRUST_UNAVAILABLE = "trust_unavailable"


class ExtensionPayloadFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1, max_length=240)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size: int = Field(ge=0, le=10_485_760)

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        if value.startswith(("/", "\\")) or "\\" in value or ".." in value or "\x00" in value:
            raise ValueError("Extension package paths must be normalized relative paths")
        return value


class ExtensionManifest(BaseModel):
    """Validated local extension metadata; unrecognized fields are rejected."""

    model_config = ConfigDict(extra="forbid")
    package_format: Literal["aurora-extension/v1"]
    id: str = Field(min_length=3, max_length=120, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    display_name: str = Field(min_length=2, max_length=120)
    version: str = Field(min_length=3, max_length=32, pattern=r"^\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]+)?$")
    description: str = Field(min_length=8, max_length=500)
    kind: ExtensionKind
    permissions: list[ExtensionPermission] = Field(default_factory=list, max_length=8)
    entrypoint: str | None = Field(default=None, max_length=160)
    connector_provider: Literal["github", "revit"] | None = None
    files: list[ExtensionPayloadFile] = Field(default_factory=list, max_length=32)

    @field_validator("entrypoint")
    @classmethod
    def validate_entrypoint(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if value.startswith(("/", "\\")) or ".." in value or ":" in value or "\\" in value:
            raise ValueError("Extension entrypoint must be a relative local filename")
        if not value.startswith("payload/") or not value.endswith((".js", ".py")):
            raise ValueError("Extension entrypoint must be a JavaScript or Python file")
        return value

    @field_validator("permissions")
    @classmethod
    def unique_permissions(cls, value: list[ExtensionPermission]) -> list[ExtensionPermission]:
        if len(value) != len(set(value)):
            raise ValueError("Extension permissions must be unique")
        return value

    @model_validator(mode="after")
    def validate_payload_contract(self) -> "ExtensionManifest":
        paths = [item.path for item in self.files]
        if len(paths) != len(set(paths)):
            raise ValueError("Extension package file paths must be unique")
        if self.kind is ExtensionKind.SANDBOXED_TOOL:
            if not self.entrypoint or self.entrypoint not in paths:
                raise ValueError("Sandboxed extensions require an indexed payload entrypoint")
        elif self.files:
            raise ValueError("Only sandboxed extensions may include executable payload files")
        return self


class ExtensionInstallRequest(BaseModel):
    extension_id: str = Field(min_length=3, max_length=120, pattern=r"^[a-z0-9][a-z0-9._-]*$")


class ExtensionUpdateRequest(BaseModel):
    enabled: bool | None = None
    configuration: dict[str, Any] | None = None

    @field_validator("configuration")
    @classmethod
    def configuration_must_not_include_secrets(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return value
        blocked = {"token", "secret", "password", "authorization", "api_key", "credential"}
        if any(key.lower().replace("-", "_") in blocked for key in value):
            raise ValueError("Extension credentials are not accepted in configuration")
        return value


class ExtensionResponse(BaseModel):
    id: str
    extension_id: str
    display_name: str
    version: str
    description: str
    kind: ExtensionKind
    permissions: list[ExtensionPermission] = Field(default_factory=list)
    enabled: bool
    status: str
    signature_status: ExtensionSignatureStatus
    signer_key_id: str | None = None
    package_sha256: str | None = None
    verified_at: datetime | None = None
    configuration: dict[str, Any] = Field(default_factory=dict)
    last_error: str | None = None
    last_run_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None


class ExtensionCatalogItem(ExtensionManifest):
    installed: bool = False
    enabled: bool = False
    status: str | None = None
    configuration: dict[str, Any] = Field(default_factory=dict)
    last_error: str | None = None
    signature_status: ExtensionSignatureStatus = ExtensionSignatureStatus.VERIFIED
    signer_key_id: str | None = None
    package_sha256: str | None = None
    verified_at: datetime | None = None


class ExtensionCatalogResponse(BaseModel):
    extensions: list[ExtensionCatalogItem] = Field(default_factory=list)


class ExtensionExecutionResponse(BaseModel):
    extension_id: str
    state: Literal["completed", "failed", "blocked"]
    message: str
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""


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


class AgentLoopStatus(str, Enum):
    IDLE = "idle"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    COMPLETED = "completed"


class AgentLoopSchedule(BaseModel):
    frequency: Literal["daily"] = "daily"
    times_per_day: int = Field(default=5, ge=5, le=5)
    duration_days: int = Field(default=7, ge=7, le=7)
    start_time: str = Field(default="08:00", pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    end_time: str = Field(default="20:00", pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    time_zone: Literal["UTC"] = "UTC"


class AgentLoopScope(BaseModel):
    areas: list[Literal["code", "tests", "docs", "ui", "connectors", "security"]] = Field(default_factory=lambda: ["code", "tests", "ui", "connectors"], min_length=1, max_length=6)
    max_actions_per_loop: int = Field(default=8, ge=1, le=8)
    allow_destructive_actions: Literal[False] = False


class AgentLoopGuardrails(BaseModel):
    max_loops_total: int = Field(default=35, ge=1, le=35)
    max_consecutive_failures: int = Field(default=3, ge=1, le=3)
    require_approval_for: list[Literal["deploy", "release", "delete", "external"]] = Field(default_factory=lambda: ["deploy", "release", "delete", "external"])
    rollback_on_error: bool = True

    @field_validator("require_approval_for")
    @classmethod
    def preserve_required_approvals(cls, value: list[str]) -> list[str]:
        if not {"deploy", "release", "delete", "external"}.issubset(set(value)):
            raise ValueError("deploy, release, delete, and external must always require approval")
        return value


class AgentLoopReporting(BaseModel):
    summary_after_each_loop: bool = True
    daily_digest: bool = True
    final_report: bool = True
    notification_channel: Literal["ui"] = "ui"


class AgentLoopRepositoryPolicy(BaseModel):
    branch_prefix: str = Field(default="aurora-agent/loop", min_length=3, max_length=80, pattern=r"^[A-Za-z0-9._/-]+$")
    allow_review_branch_push: bool = True
    allow_merge: Literal[False] = False
    allow_deploy: Literal[False] = False
    allow_release: Literal[False] = False


class AgentLoopConfig(BaseModel):
    enabled: bool = False
    dry_run: Literal[True] = True
    schedule: AgentLoopSchedule = Field(default_factory=AgentLoopSchedule)
    scope: AgentLoopScope = Field(default_factory=AgentLoopScope)
    guardrails: AgentLoopGuardrails = Field(default_factory=AgentLoopGuardrails)
    reporting: AgentLoopReporting = Field(default_factory=AgentLoopReporting)
    repository: AgentLoopRepositoryPolicy = Field(default_factory=AgentLoopRepositoryPolicy)


class AgentLoopCreate(BaseModel):
    name: str = Field(default="Repository improvement loop", min_length=3, max_length=120)
    config: AgentLoopConfig = Field(default_factory=AgentLoopConfig)


class AgentLoopUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=120)
    config: dict[str, Any] | None = None


class AgentLoopResponse(BaseModel):
    id: str
    name: str
    enabled: bool
    hard_stop: bool
    status: AgentLoopStatus
    config: dict[str, Any]
    runs_completed: int
    consecutive_failures: int
    next_run_at: datetime | None = None
    started_at: datetime | None = None
    ends_at: datetime | None = None
    last_error: str | None = None
    latest_report: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime | None = None


class AgentLoopListResponse(BaseModel):
    loops: list[AgentLoopResponse]
    count: int


class AgentLoopIterationResponse(BaseModel):
    id: str
    loop_id: str
    sequence: int
    status: Literal["planning", "completed", "failed"]
    dry_run: bool
    branch_name: str | None = None
    plan_path: str | None = None
    log_path: str | None = None
    report_path: str | None = None
    plan: dict[str, Any] = Field(default_factory=dict)
    actions: list[dict[str, Any]] = Field(default_factory=list)
    reflection: dict[str, Any] = Field(default_factory=dict)
    validation: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    started_at: datetime
    completed_at: datetime | None = None


class AgentLoopIterationListResponse(BaseModel):
    iterations: list[AgentLoopIterationResponse]
    count: int


class HealthRetentionUpdateRequest(BaseModel):
    retention_days: Literal[7, 30, 90]


class HealthRetentionResponse(BaseModel):
    retention_days: Literal[7, 30, 90]
    pruned_audit_events: int = 0
    pruned_loop_iterations: int = 0
