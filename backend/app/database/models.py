from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def generate_uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    tasks: Mapped[list["Task"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    sessions: Mapped[list["UserSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    connectors: Mapped[list["Connector"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    connector_credentials: Mapped[list["ConnectorCredential"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    agent_loops: Mapped[list["AgentLoop"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    extension_installations: Mapped[list["ExtensionInstallation"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    order: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="created", index=True)
    current_step_index: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[str | None] = mapped_column(Text)
    final_output: Mapped[dict | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(Text)
    context: Mapped[dict] = mapped_column(JSON, default=dict)
    estimated_complexity: Mapped[str] = mapped_column(String(20), default="moderate")
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user: Mapped[User] = relationship(back_populates="tasks")
    steps: Mapped[list["Step"]] = relationship(back_populates="task", cascade="all, delete-orphan", order_by="Step.order")


class Step(Base):
    __tablename__ = "steps"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    description: Mapped[str] = mapped_column(Text)
    order: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    tools_required: Mapped[list] = mapped_column(JSON, default=list)
    dependencies: Mapped[list] = mapped_column(JSON, default=list)
    input_data: Mapped[dict] = mapped_column(JSON, default=dict)
    output_data: Mapped[dict | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(Text)
    tool_calls: Mapped[list] = mapped_column(JSON, default=list)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    approval_given: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    task: Mapped[Task] = relationship(back_populates="steps")


class UserSession(Base):
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_activity: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    user: Mapped[User] = relationship(back_populates="sessions")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    event_type: Mapped[str] = mapped_column(String(50), index=True)
    resource_type: Mapped[str | None] = mapped_column(String(50))
    resource_id: Mapped[str | None] = mapped_column(String(36))
    details: Mapped[dict | None] = mapped_column(JSON)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class ConnectorCredential(Base):
    """Encrypted secret material. Ciphertext must never cross the API boundary."""

    __tablename__ = "connector_credentials"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(32), index=True)
    label: Mapped[str] = mapped_column(String(120))
    ciphertext: Mapped[str] = mapped_column(Text)
    key_version: Mapped[str] = mapped_column(String(32), default="fernet-v1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    user: Mapped[User] = relationship(back_populates="connector_credentials")
    connectors: Mapped[list["Connector"]] = relationship(back_populates="credential")


class Connector(Base):
    __tablename__ = "connectors"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(32), index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(32), default="not_configured", index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    configuration: Mapped[dict] = mapped_column(JSON, default=dict)
    credential_id: Mapped[str | None] = mapped_column(ForeignKey("connector_credentials.id", ondelete="SET NULL"), nullable=True)
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    user: Mapped[User] = relationship(back_populates="connectors")
    credential: Mapped[ConnectorCredential | None] = relationship(back_populates="connectors")
    operations: Mapped[list["ConnectorOperation"]] = relationship(back_populates="connector", cascade="all, delete-orphan")


class ConnectorOperation(Base):
    __tablename__ = "connector_operations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    connector_id: Mapped[str] = mapped_column(ForeignKey("connectors.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(32), index=True)
    operation_type: Mapped[str] = mapped_column(String(64), index=True)
    state: Mapped[str] = mapped_column(String(32), default="planned", index=True)
    request_hash: Mapped[str] = mapped_column(String(64))
    request_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    preview: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[dict | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(String(500))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    connector: Mapped[Connector] = relationship(back_populates="operations")


class ExtensionInstallation(Base):
    """A user-scoped activation record for a reviewed, local extension manifest.

    Extension source is never copied into the database and no remote package URL is
    stored.  The installed record only references a manifest that the local
    registry can still validate on every lifecycle transition.
    """

    __tablename__ = "extension_installations"
    __table_args__ = (UniqueConstraint("user_id", "extension_id", name="uq_extension_installation_user_extension"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    extension_id: Mapped[str] = mapped_column(String(120), index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    version: Mapped[str] = mapped_column(String(32))
    kind: Mapped[str] = mapped_column(String(32))
    manifest: Mapped[dict] = mapped_column(JSON, default=dict)
    configuration: Mapped[dict] = mapped_column(JSON, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="installed", index=True)
    last_error: Mapped[str | None] = mapped_column(String(500))
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    user: Mapped[User] = relationship(back_populates="extension_installations")


class AgentLoop(Base):
    """User-scoped configuration and durable lifecycle state for one bounded loop."""

    __tablename__ = "agent_loops"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120), default="Repository improvement loop")
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    hard_stop: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="idle", index=True)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    runs_completed: Mapped[int] = mapped_column(Integer, default=0)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(String(500))
    latest_report: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    user: Mapped[User] = relationship(back_populates="agent_loops")
    iterations: Mapped[list["AgentLoopIteration"]] = relationship(back_populates="loop", cascade="all, delete-orphan", order_by="AgentLoopIteration.sequence")


class AgentLoopIteration(Base):
    """One immutable plan/action/reflection record. Secret values are never stored here."""

    __tablename__ = "agent_loop_iterations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    loop_id: Mapped[str] = mapped_column(ForeignKey("agent_loops.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    sequence: Mapped[int] = mapped_column(Integer, index=True)
    status: Mapped[str] = mapped_column(String(32), default="planned", index=True)
    dry_run: Mapped[bool] = mapped_column(Boolean, default=True)
    branch_name: Mapped[str | None] = mapped_column(String(180))
    plan_path: Mapped[str | None] = mapped_column(String(500))
    log_path: Mapped[str | None] = mapped_column(String(500))
    report_path: Mapped[str | None] = mapped_column(String(500))
    plan: Mapped[dict] = mapped_column(JSON, default=dict)
    actions: Mapped[list] = mapped_column(JSON, default=list)
    reflection: Mapped[dict] = mapped_column(JSON, default=dict)
    validation: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(String(500))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    loop: Mapped[AgentLoop] = relationship(back_populates="iterations")
