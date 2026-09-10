"""Provider-neutral planner. The agent PROPOSES; it never decides safety and never executes.

DemoPlanner is deterministic and needs no external API, so the demo cannot fail
because a model endpoint is down.
"""

from __future__ import annotations

import re

from app.security.intent import RESOURCE_ALIASES, infer_op_class
from app.security.registry import OP_DELETE, OP_DROP, OP_EXPORT, OP_READ, OP_WRITE

AGENT_ID = "aegis-demo-planner"


def _resource_from(text: str, default: str = "users") -> str:
    lowered = (text or "").lower()
    best, best_pos = default, len(lowered) + 1
    for resource, aliases in RESOURCE_ALIASES.items():
        for alias in aliases:
            pos = lowered.find(alias)
            if pos != -1 and pos < best_pos:
                best, best_pos = resource, pos
    return best


def plan(user_request: str) -> dict:
    """Turn a natural-language request into a single proposed tool call."""
    text = (user_request or "").strip()
    lowered = text.lower()
    resource = _resource_from(text)
    op = infer_op_class(text) or OP_READ

    if re.search(r"\b(list|show)\s+(all\s+)?(tables|resources)\b", lowered):
        return {"action": "list_tables", "resource": resource, "parameters": {}}

    if op == OP_DROP:
        return {"action": "drop_table", "resource": resource, "parameters": {}}

    if op == OP_DELETE:
        everything = bool(re.search(r"\b(all|everything|every|entire)\b", lowered)) or \
            "clean" in lowered or "clear" in lowered
        return {"action": "delete_records", "resource": resource,
                "parameters": {"filter": "all" if everything else {"id": "1"}}}

    if op == OP_EXPORT:
        if any(word in lowered for word in ("email", "mail", "send", "notify")):
            return {"action": "send_email", "resource": "mock_email",
                    "parameters": {"to": "ops@example.com", "subject": "AEGIS demo"}}
        return {"action": "export_data", "resource": resource,
                "parameters": {"destination": "mock://export"}}

    if op == OP_WRITE:
        if any(word in lowered for word in ("insert", "add", "create", "new")):
            return {"action": "insert_record", "resource": resource,
                    "parameters": {"payload": {"value": "created by agent"}}}
        return {"action": "update_record", "resource": resource,
                "parameters": {"filter": {"id": "1"}, "changes": {"value": "updated by agent"}}}

    return {"action": "read_table", "resource": resource, "parameters": {"limit": 10}}
