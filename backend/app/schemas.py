"""Pydantic request/response schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Liveness and dependency status."""

    status: Literal["ok", "degraded"] = Field(..., description="Overall service status")
    service: str = Field(..., description="Service identifier")
    database: Literal["ok", "unavailable"] = Field(..., description="Database connectivity")
    timestamp: str = Field(..., description="UTC ISO-8601 timestamp")
    trace_id: str | None = Field(None, description="Correlation id for this request")

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "ok",
                "service": "aegis-backend",
                "database": "ok",
                "timestamp": "2026-09-10T12:00:00Z",
                "trace_id": "9f1c0f7a2b4d4e8fa1c3d5e7b9a0c2d4",
            }
        }
    }


class VersionResponse(BaseModel):
    """Build and deployment identity."""

    service: str = Field(..., description="Service identifier")
    version: str = Field(..., description="Semantic version")
    phase: str = Field(..., description="Project phase")
    environment: str = Field(..., description="Deployment environment")
    schema_version: int | None = Field(None, description="Applied database schema version")

    model_config = {
        "json_schema_extra": {
            "example": {
                "service": "aegis-backend",
                "version": "0.1.0",
                "phase": "0 - foundation",
                "environment": "development",
                "schema_version": 1,
            }
        }
    }
