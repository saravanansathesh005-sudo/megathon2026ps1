"""ORM models.

Phase 0 defines only the schema-version marker, which exists so that database
initialisation is observable and testable. Domain models (actions, decisions,
approvals, audit chain) arrive in later phases.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.db import Base
from app.logging_config import utc_now

# Bump when the schema changes.
SCHEMA_VERSION = 1


class SchemaVersion(Base):
    """Single-row marker recording the applied schema version."""

    __tablename__ = "schema_version"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    note: Mapped[str] = mapped_column(String(255), nullable=False, default="")

    @classmethod
    def ensure(cls, session: Session, version: int) -> "SchemaVersion":
        """Insert the version marker if it is not already present."""
        existing = session.scalar(select(cls).where(cls.version == version))
        if existing is not None:
            return existing

        row = cls(version=version, applied_at=utc_now(), note="phase-0 foundation")
        session.add(row)
        session.flush()
        return row

    @classmethod
    def current(cls, session: Session) -> int | None:
        """Return the highest applied schema version, or None if uninitialised."""
        return session.scalar(select(cls.version).order_by(cls.version.desc()).limit(1))

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<SchemaVersion version={self.version}>"
