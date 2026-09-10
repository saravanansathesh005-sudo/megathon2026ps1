"""Shared pytest fixtures."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

_TMP_DIR = tempfile.mkdtemp(prefix="aegis-tests-")
_TEST_DB = Path(_TMP_DIR) / "test_aegis.db"

os.environ["DATABASE_URL"] = "sqlite:///" + _TEST_DB.as_posix()
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault("APPROVAL_TTL_SECONDS", "180")


@pytest.fixture(scope="session")
def test_db_path() -> Path:
    return _TEST_DB


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def _fresh_state(client):
    """Reset the demo dataset before every test so trajectories stay deterministic."""
    client.post("/api/demo/reset")
    yield


def _login(client, username: str, password: str) -> dict:
    response = client.post("/api/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    body = response.json()
    return {"Authorization": "Bearer " + body["token"], "_body": body}


@pytest.fixture
def viewer(client):
    return _login(client, "viewer", "viewer123")


@pytest.fixture
def editor(client):
    return _login(client, "editor", "editor123")


@pytest.fixture
def admin(client):
    return _login(client, "admin", "admin123")


@pytest.fixture
def secadmin(client):
    return _login(client, "secadmin", "secadmin123")


def auth(headers: dict) -> dict:
    return {"Authorization": headers["Authorization"]}


@pytest.fixture
def db_session():
    from app.db import SessionLocal

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="session", autouse=True)
def _cleanup():
    yield
    try:
        from app.db import engine

        engine.dispose()
    except Exception:
        pass
    try:
        if _TEST_DB.exists():
            _TEST_DB.unlink()
        Path(_TMP_DIR).rmdir()
    except OSError:
        pass
