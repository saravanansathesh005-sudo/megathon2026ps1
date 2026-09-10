"""ORM models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, select,
)
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship

from app.db import Base
from app.logging_config import utc_now

SCHEMA_VERSION = 2


class SchemaVersion(Base):
    __tablename__ = "schema_version"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    note: Mapped[str] = mapped_column(String(255), default="")

    @classmethod
    def ensure(cls, session: Session, version: int) -> "SchemaVersion":
        row = session.scalar(select(cls).where(cls.version == version))
        if row:
            return row
        row = cls(version=version, applied_at=utc_now(), note="aegis")
        session.add(row)
        session.flush()
        return row

    @classmethod
    def current(cls, session: Session) -> int | None:
        return session.scalar(select(cls.version).order_by(cls.version.desc()).limit(1))


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32))  # viewer|editor|admin|security_admin
    display_name: Mapped[str] = mapped_column(String(128), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class UserSession(Base):
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    agent_id: Mapped[str] = mapped_column(String(64), default="aegis-demo-planner")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Resource(Base):
    __tablename__ = "resources"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    kind: Mapped[str] = mapped_column(String(32), default="table")
    is_production: Mapped[bool] = mapped_column(Boolean, default=False)
    is_sensitive: Mapped[bool] = mapped_column(Boolean, default=False)
    criticality: Mapped[str] = mapped_column(String(16), default="low")  # low|medium|high|critical
    is_disposable: Mapped[bool] = mapped_column(Boolean, default=False)
    dropped: Mapped[bool] = mapped_column(Boolean, default=False)


class ResourceDependency(Base):
    """`dependent` breaks if `depends_on` is damaged."""

    __tablename__ = "resource_dependencies"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dependent_id: Mapped[int] = mapped_column(ForeignKey("resources.id"), index=True)
    depends_on_id: Mapped[int] = mapped_column(ForeignKey("resources.id"), index=True)


class Record(Base):
    """Generic row store the mock tools operate on."""

    __tablename__ = "records"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    resource_id: Mapped[int] = mapped_column(ForeignKey("resources.id"), index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)


class Action(Base):
    __tablename__ = "actions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    username: Mapped[str] = mapped_column(String(64))
    role: Mapped[str] = mapped_column(String(32))
    agent_id: Mapped[str] = mapped_column(String(64))
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    trace_id: Mapped[str] = mapped_column(String(64), default="")

    user_request: Mapped[str] = mapped_column(Text, default="")
    action_name: Mapped[str] = mapped_column(String(64), index=True)
    resource_name: Mapped[str] = mapped_column(String(64), default="")
    parameters: Mapped[dict] = mapped_column(JSON, default=dict)
    action_hash: Mapped[str] = mapped_column(String(64), index=True)

    analysis: Mapped[dict] = mapped_column(JSON, default=dict)
    decision: Mapped[str] = mapped_column(String(32), index=True)
    blast_radius: Mapped[float] = mapped_column(Float, default=0.0)
    reversibility: Mapped[str] = mapped_column(String(4), default="R0")
    trajectory_score: Mapped[int] = mapped_column(Integer, default=0)
    intent_status: Mapped[str] = mapped_column(String(32), default="")
    authorized: Mapped[bool] = mapped_column(Boolean, default=False)

    execution_status: Mapped[str] = mapped_column(String(32), default="not_executed")
    verification_status: Mapped[str] = mapped_column(String(32), default="not_verified")
    commit_status: Mapped[str] = mapped_column(String(32), default="none")
    result: Mapped[dict] = mapped_column(JSON, default=dict)


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action_id: Mapped[int] = mapped_column(ForeignKey("actions.id"), index=True)
    requester_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    requester_session_id: Mapped[str] = mapped_column(String(64))
    action_hash: Mapped[str] = mapped_column(String(64))
    required_level: Mapped[str] = mapped_column(String(32))  # confirmation|admin_approval
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    approved_by_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consumed: Mapped[bool] = mapped_column(Boolean, default=False)
    reason: Mapped[str] = mapped_column(Text, default="")


class Snapshot(Base):
    __tablename__ = "snapshots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action_id: Mapped[int] = mapped_column(ForeignKey("actions.id"), index=True)
    resource_name: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    state: Mapped[dict] = mapped_column(JSON, default=dict)
    restored: Mapped[bool] = mapped_column(Boolean, default=False)


class ActionEvent(Base):
    """Tamper-evident audit chain."""

    __tablename__ = "action_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    action_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(48))
    username: Mapped[str] = mapped_column(String(64), default="")
    agent_id: Mapped[str] = mapped_column(String(64), default="")
    session_id: Mapped[str] = mapped_column(String(64), default="")
    action_name: Mapped[str] = mapped_column(String(64), default="")
    resource_name: Mapped[str] = mapped_column(String(64), default="")
    decision: Mapped[str] = mapped_column(String(32), default="")
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    previous_hash: Mapped[str] = mapped_column(String(64), default="")
    current_hash: Mapped[str] = mapped_column(String(64), default="", index=True)
