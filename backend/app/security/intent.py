"""Intent boundary. Deterministic - no LLM.

Two independent bounds:
  1. the user's stated request
  2. the sanctioned envelope of the identity's role
An action outside either is not within scope.
"""

from __future__ import annotations

import re

from app.security.registry import (
    ACTIONS, OP_DELETE, OP_DROP, OP_EXPORT, OP_READ, OP_SEVERITY, OP_WRITE,
    is_known, role_max_severity,
)

WITHIN_SCOPE, SCOPE_EXPANSION, OUT_OF_SCOPE = "WITHIN_SCOPE", "SCOPE_EXPANSION", "OUT_OF_SCOPE"

VERBS = {
    OP_DROP: ["drop", "destroy", "wipe", "obliterate"],
    OP_DELETE: ["delete", "remove", "clean", "clear", "purge", "truncate", "erase"],
    OP_EXPORT: ["export", "download", "dump", "extract", "email", "send", "share", "exfiltrate"],
    OP_WRITE: ["update", "change", "edit", "modify", "set", "insert", "add", "create", "write"],
    OP_READ: ["show", "list", "read", "view", "get", "display", "fetch", "see", "find", "count"],
}

RESOURCE_ALIASES = {
    "users": ["user", "users", "customer", "customers", "account", "accounts"],
    "orders": ["order", "orders", "purchase", "purchases"],
    "test_table": ["test", "test table", "test_table", "test data", "testing", "disposable", "scratch"],
    "audit_demo": ["audit", "audit_demo", "audit demo"],
    "mock_email": ["email", "emails", "mail", "mock_email"],
    "mock_files": ["mock_files"],
    "projects": ["project", "projects"],
    "tasks": ["task", "tasks", "todo", "to-do"],
    "files": ["file", "files", "document", "documents", "note", "notes"],
}


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z_]+", (text or "").lower())


def infer_op_class(text: str) -> str | None:
    words = set(_tokens(text))
    lowered = (text or "").lower()
    for op in (OP_DROP, OP_DELETE, OP_EXPORT, OP_WRITE, OP_READ):
        for verb in VERBS[op]:
            if verb in words or verb in lowered:
                return op
    return None


def infer_resources(text: str) -> set[str]:
    lowered = (text or "").lower()
    found = set()
    for resource, aliases in RESOURCE_ALIASES.items():
        if any(alias in lowered for alias in aliases):
            found.add(resource)
    return found


def check(user_request: str, action_name: str, resource_name: str, role: str) -> dict:
    if not is_known(action_name):
        return {"status": OUT_OF_SCOPE, "reason": f"unknown action '{action_name}'",
                "requested_op": None, "action_op": None, "severity_delta": None}

    action_op = ACTIONS[action_name].op_class
    action_sev = OP_SEVERITY[action_op]
    reasons = []

    # Bound 2: the role's sanctioned envelope.
    max_sev = role_max_severity(role)
    if action_sev > max_sev:
        return {
            "status": OUT_OF_SCOPE,
            "reason": f"'{action_op}' exceeds the sanctioned envelope of role '{role}'",
            "requested_op": infer_op_class(user_request), "action_op": action_op,
            "severity_delta": action_sev - max_sev,
        }

    # Bound 1: the stated request.
    requested_op = infer_op_class(user_request)
    requested_resources = infer_resources(user_request)

    if requested_resources and resource_name and resource_name not in requested_resources:
        return {
            "status": OUT_OF_SCOPE,
            "reason": f"action targets '{resource_name}' but the request named "
                      f"{sorted(requested_resources)}",
            "requested_op": requested_op, "action_op": action_op, "severity_delta": None,
        }

    if requested_op is None:
        status = WITHIN_SCOPE if action_sev == 0 else SCOPE_EXPANSION
        return {"status": status, "reason": "no explicit operation in the request",
                "requested_op": None, "action_op": action_op, "severity_delta": None}

    delta = action_sev - OP_SEVERITY[requested_op]
    if delta <= 0:
        status, reason = WITHIN_SCOPE, f"'{action_op}' is within a '{requested_op}' request"
    elif delta == 1:
        status, reason = SCOPE_EXPANSION, f"'{action_op}' widens a '{requested_op}' request"
    else:
        status, reason = OUT_OF_SCOPE, f"'{action_op}' far exceeds a '{requested_op}' request"

    reasons.append(reason)
    return {"status": status, "reason": reason, "requested_op": requested_op,
            "action_op": action_op, "severity_delta": delta}
