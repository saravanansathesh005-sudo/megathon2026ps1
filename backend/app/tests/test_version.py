"""Acceptance tests for GET /api/version."""

from __future__ import annotations

from app import __version__


def test_version_returns_identity(client):
    response = client.get("/api/version")

    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "aegis-backend"
    assert body["version"] == __version__
    assert body["environment"] == "test"


def test_version_reports_applied_schema_version(client):
    body = client.get("/api/version").json()

    assert body["schema_version"] == 1
