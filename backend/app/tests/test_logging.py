"""Structured logging tests.

The log contract is: timestamp, level, service, trace_id, event — every record,
every time. Later phases build the audit trail on top of this.
"""

from __future__ import annotations

import json
import logging

from app.logging_config import (
    JsonFormatter,
    get_trace_id,
    new_trace_id,
    set_trace_id,
    utc_now,
    utc_now_iso,
)

REQUIRED_FIELDS = {"timestamp", "level", "service", "trace_id", "event"}


def _emit(event: str, level: int = logging.INFO, **extra) -> dict:
    record = logging.LogRecord(
        name="test", level=level, pathname=__file__, lineno=1,
        msg=event, args=(), exc_info=None,
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return json.loads(JsonFormatter("aegis-backend").format(record))


def test_record_contains_required_fields():
    payload = _emit("test.event")

    assert REQUIRED_FIELDS.issubset(payload.keys())


def test_event_is_the_log_message():
    assert _emit("db.initialized")["event"] == "db.initialized"


def test_level_and_service_are_reported():
    payload = _emit("test.event", level=logging.WARNING)

    assert payload["level"] == "WARNING"
    assert payload["service"] == "aegis-backend"


def test_trace_id_is_bound_from_context():
    trace_id = new_trace_id()
    set_trace_id(trace_id)

    assert _emit("test.event")["trace_id"] == trace_id
    assert get_trace_id() == trace_id


def test_context_is_included_when_supplied():
    payload = _emit("tool.invoked", context={"tool": "read_table", "rows": 42})

    assert payload["context"] == {"tool": "read_table", "rows": 42}


def test_timestamp_is_utc_iso_with_z():
    payload = _emit("test.event")

    assert payload["timestamp"].endswith("Z")
    assert "T" in payload["timestamp"]


def test_utc_helpers_are_timezone_aware():
    assert utc_now().tzinfo is not None
    assert utc_now().utcoffset().total_seconds() == 0
    assert utc_now_iso().endswith("Z")


def test_output_is_single_line_json():
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname=__file__, lineno=1,
        msg="multi.line", args=(), exc_info=None,
    )
    rendered = JsonFormatter("aegis-backend").format(record)

    assert "\n" not in rendered
    json.loads(rendered)
