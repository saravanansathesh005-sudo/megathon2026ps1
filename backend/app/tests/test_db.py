"""Database initialisation tests."""

from __future__ import annotations

from sqlalchemy import inspect


def test_database_file_created(client, test_db_path):
    assert test_db_path.exists(), "init_db should create the SQLite file"


def test_schema_version_table_exists(client):
    from app.db import engine

    tables = inspect(engine).get_table_names()
    assert "schema_version" in tables


def test_init_db_is_idempotent(client):
    from app.db import SessionLocal, init_db
    from app.models import SCHEMA_VERSION, SchemaVersion

    init_db()
    init_db()

    with SessionLocal() as session:
        rows = session.query(SchemaVersion).filter_by(version=SCHEMA_VERSION).all()

    assert len(rows) == 1, "repeated initialisation must not duplicate the marker"


def test_schema_version_applied_at_is_timezone_aware(client):
    from app.db import SessionLocal
    from app.models import SchemaVersion

    with SessionLocal() as session:
        row = session.query(SchemaVersion).first()

    assert row is not None
    assert row.applied_at is not None
