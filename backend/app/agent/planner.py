"""Deterministic fallback planner.

The agent PROPOSES; it never decides safety and never executes. This planner needs no
external API, so the system keeps working when Gemini is unavailable.
"""

from __future__ import annotations

import re

from app.security.intent import RESOURCE_ALIASES, infer_op_class
from app.security.registry import OP_DELETE, OP_DROP, OP_EXPORT, OP_READ, OP_WRITE

AGENT_ID = "aegis-planner"

# Workspace nouns -> the resource they name.
WORKSPACE_NOUNS = {
    "projects": ["project", "projects"],
    "tasks": ["task", "tasks", "todo", "to-do"],
    "files": ["file", "files", "document", "documents", "note", "notes"],
}

SINGULAR = {"projects": "project", "tasks": "task", "files": "file"}


_STOPWORDS = {"the", "a", "an", "my", "all", "every", "this", "that", "these",
              "those", "for", "of", "to", "and", "with", "from", "in", "on", "it"}


def _quoted_name(text: str, noun: str | None = None) -> str | None:
    quoted = re.search(r"[\"'‘’“”]([^\"'‘’“”]{1,80})", text)
    if quoted:
        return quoted.group(1).strip()
    named = re.search(r"\b(?:called|named|titled)\s+([\w\- .]{1,60})", text, re.IGNORECASE)
    if named:
        return named.group(1).strip().rstrip(".!?")
    if noun:
        # "delete the project Portfolio" / "delete project Portfolio"
        after = re.search(r"\b" + re.escape(noun) + r"\s+([A-Za-z0-9][\w\-.]{0,58})",
                          text, re.IGNORECASE)
        if after:
            candidate = after.group(1).strip().rstrip(".!?")
            if candidate.lower() not in _STOPWORDS:
                return candidate
    return None


def _workspace_target(text: str) -> str | None:
    lowered = (text or "").lower()
    best, best_pos = None, len(lowered) + 1
    for resource, nouns in WORKSPACE_NOUNS.items():
        for noun in nouns:
            pos = re.search(r"\b" + re.escape(noun) + r"\b", lowered)
            if pos and pos.start() < best_pos:
                best, best_pos = resource, pos.start()
    return best


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
    op = infer_op_class(text) or OP_READ
    workspace = _workspace_target(text)
    everything = bool(re.search(r"\b(all|every|everything|entire)\b", lowered))

    # ------------------------------------------------------- workspace domain first
    if workspace:
        singular = SINGULAR[workspace]
        name = _quoted_name(text, singular)
        if op in (OP_DELETE, OP_DROP):
            if everything and workspace == "projects":
                return {"action": "delete_all_projects", "resource": "projects",
                        "parameters": {}}
            return {"action": "delete_" + singular, "resource": workspace,
                    "parameters": {"name": name} if name else {}}
        if op == OP_WRITE:
            if any(w in lowered for w in ("create", "add", "new", "make", "start")):
                return {"action": "create_" + singular, "resource": workspace,
                        "parameters": {"name": name or "Untitled " + singular}}
            if workspace == "files" and "move" in lowered:
                return {"action": "move_files", "resource": "files",
                        "parameters": {"to": "/archive"}}
            if everything:
                return {"action": "bulk_update", "resource": workspace,
                        "parameters": {"changes": {"status": "updated"}}}
            return {"action": "update_" + singular, "resource": workspace,
                    "parameters": {"name": name, "changes": {"status": "updated"}}}
        if op == OP_EXPORT:
            return {"action": "export_data", "resource": workspace,
                    "parameters": {"destination": "mock://export"}}
        return {"action": "list_" + workspace, "resource": workspace, "parameters": {}}

    # ---------------------------------------------------------- explicit bypass asks
    if re.search(r"\b(disable|turn off)\s+(aegis|security)", lowered):
        return {"action": "disable_security", "resource": "", "parameters": {}}
    if re.search(r"\b(another|other)\s+user('s)?\s+(data|files?|projects?|account)", lowered):
        return {"action": "access_other_user_data", "resource": "users", "parameters": {}}
    if re.search(r"\b(make|grant|give)\s+(me|myself)\s+(an?\s+)?(admin|root)", lowered):
        return {"action": "escalate_privilege", "resource": "", "parameters": {}}
    if re.search(r"\b(delete|clear|wipe)\s+(the\s+)?(audit|logs?)\b", lowered):
        return {"action": "modify_audit_log", "resource": "audit_demo", "parameters": {}}

    # ------------------------------------------------------------- legacy data plane
    resource = _resource_from(text)

    if re.search(r"\b(list|show)\s+(all\s+)?(tables|resources)\b", lowered):
        return {"action": "list_tables", "resource": resource, "parameters": {}}

    if op == OP_DROP:
        return {"action": "drop_table", "resource": resource, "parameters": {}}

    if op == OP_DELETE:
        wipe = everything or "clean" in lowered or "clear" in lowered
        return {"action": "delete_records", "resource": resource,
                "parameters": {"filter": "all" if wipe else {"id": "1"}}}

    if op == OP_EXPORT:
        if any(word in lowered for word in ("email", "mail", "send", "notify")):
            return {"action": "send_email", "resource": "mock_email",
                    "parameters": {"to": "ops@example.com", "subject": "AEGIS demo"}}
        if any(word in lowered for word in ("sensitive", "credential", "password", "secret")):
            return {"action": "export_sensitive", "resource": resource, "parameters": {}}
        return {"action": "export_data", "resource": resource,
                "parameters": {"destination": "mock://export"}}

    if op == OP_WRITE:
        if any(word in lowered for word in ("insert", "add", "create", "new")):
            return {"action": "insert_record", "resource": resource,
                    "parameters": {"payload": {"value": "created by agent"}}}
        return {"action": "update_record", "resource": resource,
                "parameters": {"filter": {"id": "1"}, "changes": {"value": "updated by agent"}}}

    return {"action": "read_table", "resource": resource, "parameters": {"limit": 10}}
