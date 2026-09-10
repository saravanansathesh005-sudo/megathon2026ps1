"""AEGIS backend — FastAPI application entrypoint.

Phase 0: foundation only. Health, version, database initialisation, structured
logging and request tracing. No security enforcement, no agent, no LLM.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db, init_db
from app.logging_config import (
    configure_logging,
    get_trace_id,
    new_trace_id,
    set_trace_id,
    utc_now_iso,
)
from app.models import SchemaVersion
from app.routes import router as api_router
from app.schemas import HealthResponse, VersionResponse

settings = get_settings()
configure_logging(settings.SERVICE_NAME, settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

TRACE_HEADER = "X-Trace-Id"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise the database on startup."""
    set_trace_id(new_trace_id())
    logger.info(
        "service.starting",
        extra={"context": {"version": settings.VERSION, "phase": settings.PHASE}},
    )
    init_db()
    logger.info("service.started")
    yield
    logger.info("service.stopping")


app = FastAPI(
    title="AEGIS — Autonomous Execution Guard & Impact Safety",
    description=(
        "Runtime security harness for AI agents. Phase 0 exposes only "
        "foundation endpoints; enforcement arrives in later phases."
    ),
    version=settings.VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)


@app.middleware("http")
async def trace_id_middleware(request: Request, call_next) -> Response:
    """Bind a trace id to every request and echo it on the response."""
    trace_id = request.headers.get(TRACE_HEADER) or new_trace_id()
    set_trace_id(trace_id)

    logger.info(
        "http.request.started",
        extra={"context": {"method": request.method, "path": request.url.path}},
    )

    response = await call_next(request)
    response.headers[TRACE_HEADER] = trace_id

    logger.info(
        "http.request.completed",
        extra={
            "context": {
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
            }
        },
    )
    return response


@app.get(
    f"{settings.API_PREFIX}/health",
    response_model=HealthResponse,
    tags=["system"],
    summary="Liveness and dependency check",
)
def health(db: Session = Depends(get_db)) -> HealthResponse:
    """Report service status and database connectivity."""
    try:
        db.execute(text("SELECT 1"))
        database = "ok"
    except Exception:  # pragma: no cover - exercised only on a broken database
        logger.exception("health.database_unavailable")
        database = "unavailable"

    return HealthResponse(
        status="ok" if database == "ok" else "degraded",
        service=settings.SERVICE_NAME,
        database=database,
        timestamp=utc_now_iso(),
        trace_id=get_trace_id(),
    )


@app.get(
    f"{settings.API_PREFIX}/version",
    response_model=VersionResponse,
    tags=["system"],
    summary="Build and deployment identity",
)
def version(db: Session = Depends(get_db)) -> VersionResponse:
    """Report service version, phase, environment and schema version."""
    try:
        schema_version = SchemaVersion.current(db)
    except Exception:  # pragma: no cover - exercised only on a broken database
        logger.exception("version.schema_lookup_failed")
        schema_version = None

    return VersionResponse(
        service=settings.SERVICE_NAME,
        version=settings.VERSION,
        phase=settings.PHASE,
        environment=settings.ENVIRONMENT,
        schema_version=schema_version,
    )
