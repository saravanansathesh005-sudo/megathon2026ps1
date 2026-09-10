"""Database engine, session factory, and schema initialisation."""

from __future__ import annotations

import logging
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def _engine_kwargs(database_url: str) -> dict:
    # SQLite guards against cross-thread use by default; FastAPI's threadpool
    # legitimately shares a connection, so that check is disabled here.
    if database_url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    return {}


_settings = get_settings()

engine = create_engine(
    _settings.DATABASE_URL,
    echo=False,
    future=True,
    **_engine_kwargs(_settings.DATABASE_URL),
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a scoped database session."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def init_db() -> None:
    """Create any missing tables and record the schema version."""
    from app import models  # noqa: F401  (registers models on Base.metadata)

    Base.metadata.create_all(bind=engine)

    # create_all() adds tables but never alters existing ones, so a database written
    # by an older schema fails later with a confusing "no such column". Outside
    # production we rebuild, loudly. Production needs a real migration.
    stored = None
    try:
        with SessionLocal() as probe:
            stored = models.SchemaVersion.current(probe)
    except Exception:
        stored = None

    if stored is not None and stored != models.SCHEMA_VERSION:
        if _settings.ENVIRONMENT == "production":
            raise RuntimeError("database schema is v" + str(stored) + " but the code "
                               "expects v" + str(models.SCHEMA_VERSION))
        logger.warning("db.schema_rebuild", extra={"context": {
            "found": stored, "expected": models.SCHEMA_VERSION,
            "action": "dropping and recreating the demo database"}})
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)

    with SessionLocal() as session:
        models.SchemaVersion.ensure(session, models.SCHEMA_VERSION)
        session.commit()
        from app.services import seed

        seed.ensure_seeded(session)

    logger.info(
        "db.initialized",
        extra={
            "context": {
                "tables": sorted(Base.metadata.tables),
                "schema_version": models.SCHEMA_VERSION,
            }
        },
    )
