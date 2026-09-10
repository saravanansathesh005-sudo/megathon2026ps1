"""Structured JSON logging.

Every record carries: timestamp, level, service, trace_id, event.
Timestamps are UTC, ISO-8601, with a trailing Z.

The log message *is* the event name — use dotted, machine-readable names
("http.request.completed"), and put variable data in ``extra={"context": {...}}``:

    logger.info("db.initialized", extra={"context": {"tables": 1}})
"""

from __future__ import annotations

import json
import logging
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

# Per-request correlation id. Set by TraceIdMiddleware, read by the formatter.
_trace_id_var: ContextVar[str | None] = ContextVar("trace_id", default=None)

_RESERVED = {
    "args", "asctime", "created", "exc_info", "exc_text", "filename",
    "funcName", "levelname", "levelno", "lineno", "module", "msecs",
    "message", "msg", "name", "pathname", "process", "processName",
    "relativeCreated", "stack_info", "thread", "threadName", "taskName",
    # uvicorn attaches an ANSI-coloured duplicate of the message; drop it.
    "color_message",
}


def new_trace_id() -> str:
    """Generate a fresh trace id."""
    return uuid.uuid4().hex


def set_trace_id(trace_id: str) -> None:
    """Bind a trace id to the current context."""
    _trace_id_var.set(trace_id)


def get_trace_id() -> str | None:
    """Return the trace id bound to the current context, if any."""
    return _trace_id_var.get()


def utc_now() -> datetime:
    """Current time, timezone-aware, UTC. Use this everywhere."""
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    """Current UTC time as ISO-8601 with a trailing Z."""
    return utc_now().isoformat().replace("+00:00", "Z")


class JsonFormatter(logging.Formatter):
    """Render log records as single-line JSON objects."""

    def __init__(self, service: str) -> None:
        super().__init__()
        self.service = service

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "service": self.service,
            "trace_id": get_trace_id(),
            "event": record.getMessage(),
        }

        context = getattr(record, "context", None)
        if isinstance(context, dict):
            payload["context"] = context

        # Any other non-reserved attribute passed via extra=
        for key, value in record.__dict__.items():
            if key not in _RESERVED and key not in payload and key != "context":
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def configure_logging(service: str, level: str = "INFO") -> None:
    """Install the JSON formatter on the root logger. Idempotent."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter(service))

    root = logging.getLogger()
    for existing in list(root.handlers):
        root.removeHandler(existing)
    root.addHandler(handler)
    root.setLevel(level.upper())

    # uvicorn ships its own handlers; route them through ours instead.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True
