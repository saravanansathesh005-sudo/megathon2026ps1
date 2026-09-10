"""Tamper-evident audit chain (SHA-256 hash chaining, not a blockchain)."""

from __future__ import annotations

import hashlib
import json
from datetime import timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.logging_config import utc_now
from app.models import ActionEvent

GENESIS = "0" * 64


def _ts(value) -> str:
    """Normalise to naive UTC so a value survives the SQLite round trip unchanged."""
    if value is None:
        return ""
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value.isoformat()


def canonical(event: ActionEvent) -> str:
    return json.dumps(
        {
            "timestamp": _ts(event.timestamp),
            "action_id": event.action_id,
            "event_type": event.event_type,
            "username": event.username,
            "agent_id": event.agent_id,
            "session_id": event.session_id,
            "action_name": event.action_name,
            "resource_name": event.resource_name,
            "decision": event.decision,
            "detail": event.detail,
        },
        sort_keys=True, separators=(",", ":"), default=str,
    )


def compute_hash(event: ActionEvent, previous_hash: str) -> str:
    return hashlib.sha256((canonical(event) + previous_hash).encode()).hexdigest()


def head_hash(db: Session) -> str:
    last = db.scalar(select(ActionEvent).order_by(ActionEvent.id.desc()).limit(1))
    return last.current_hash if last else GENESIS


def record(db: Session, *, event_type: str, action_id: int | None = None,
           username: str = "", agent_id: str = "", session_id: str = "",
           action_name: str = "", resource_name: str = "", decision: str = "",
           detail: dict | None = None) -> ActionEvent:
    event = ActionEvent(
        timestamp=utc_now(), action_id=action_id, event_type=event_type,
        username=username, agent_id=agent_id, session_id=session_id,
        action_name=action_name, resource_name=resource_name, decision=decision,
        detail=detail or {},
    )
    event.previous_hash = head_hash(db)
    event.current_hash = compute_hash(event, event.previous_hash)
    db.add(event)
    db.flush()
    return event


def verify_chain(db: Session) -> dict:
    events = db.scalars(select(ActionEvent).order_by(ActionEvent.id.asc())).all()
    previous = GENESIS
    for event in events:
        if event.previous_hash != previous:
            return {"valid": False, "length": len(events), "broken_at": event.id,
                    "reason": "previous_hash does not match the prior event"}
        if compute_hash(event, previous) != event.current_hash:
            return {"valid": False, "length": len(events), "broken_at": event.id,
                    "reason": "event content does not match its recorded hash"}
        previous = event.current_hash
    return {"valid": True, "length": len(events), "broken_at": None,
            "reason": "chain intact", "head": previous}
