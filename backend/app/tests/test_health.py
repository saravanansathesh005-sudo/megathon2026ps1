"""Acceptance tests for GET /api/health."""

from __future__ import annotations


def test_health_returns_ok(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert body["service"] == "aegis-backend"


def test_health_timestamp_is_utc_iso(client):
    body = client.get("/api/health").json()

    assert body["timestamp"].endswith("Z"), "timestamps must be UTC with a Z suffix"


def test_health_returns_trace_id_header(client):
    response = client.get("/api/health")

    trace_id = response.headers.get("X-Trace-Id")
    assert trace_id
    assert response.json()["trace_id"] == trace_id


def test_health_echoes_supplied_trace_id(client):
    supplied = "abc123def456"

    response = client.get("/api/health", headers={"X-Trace-Id": supplied})

    assert response.headers["X-Trace-Id"] == supplied
    assert response.json()["trace_id"] == supplied
