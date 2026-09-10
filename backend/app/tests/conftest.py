"""Shared pytest fixtures.

The database URL is redirected to a temporary file *before* the application is
imported, so tests never touch the developer's aegis.db.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

_TMP_DIR = tempfile.mkdtemp(prefix="aegis-tests-")
_TEST_DB = Path(_TMP_DIR) / "test_aegis.db"

# Must be set before app.config is imported anywhere.
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB.as_posix()}"
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("LOG_LEVEL", "WARNING")


@pytest.fixture(scope="session")
def test_db_path() -> Path:
    """Path to the temporary SQLite file used by the suite."""
    return _TEST_DB


@pytest.fixture(scope="session")
def client():
    """TestClient with the application lifespan run (so init_db executes)."""
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session", autouse=True)
def _cleanup():
    yield

    # Release the SQLite file handle before removing it.
    try:
        from app.db import engine

        engine.dispose()
    except Exception:  # pragma: no cover - engine may never have been created
        pass

    try:
        if _TEST_DB.exists():
            _TEST_DB.unlink()
        Path(_TMP_DIR).rmdir()
    except OSError:  # pragma: no cover - best-effort cleanup on Windows
        pass
