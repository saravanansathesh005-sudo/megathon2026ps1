"""Deterministic fallback planner.

The agent PROPOSES; it never decides safety and never executes. This planner needs no
external API, so the system keeps working when Gemini is unavailable.
"""

from __future__ import annotations

import re

from app.security import injection
from app.security.intent import RESOURCE_ALIASES, VERBS, infer_op_class
from app.security.registry import OP_DELETE, OP_DROP, OP_EXPORT, OP_READ, OP_WRITE

# Word-boundary token, built explicitly to survive any editing pipeline.
WORD = chr(92) + "b"

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


def _distinct_ops(text: str) -> int:
    """How many different operation classes does this message ask for?"""
    lowered = (text or "").lower()
    found = set()
    for op, verbs in VERBS.items():
        for verb in verbs:
            if re.search(WORD + re.escape(verb) + WORD, lowered):
                found.add(op)
                break
    return len(found)


_RESOURCE_WORDS = re.compile(
    WORD + r"(table|tables|record|records|row|rows|database|audit|logs?|email|emails)" + WORD)


def _names_a_resource(text: str) -> bool:
    """Does the message mention something the agent could act on?"""
    lowered = (text or "").lower()
    if _RESOURCE_WORDS.search(lowered):
        return True
    return any(alias in lowered
               for aliases in RESOURCE_ALIASES.values() for alias in aliases)


def _resource_from(text: str) -> str | None:
    """Name the resource the text refers to, or None. Never guess.

    Defaulting an unrecognised target to a real table is how "clear my stuff"
    becomes "delete every row in production users".
    """
    lowered = (text or "").lower()
    best, best_pos = None, len(lowered) + 1
    for resource, aliases in RESOURCE_ALIASES.items():
        for alias in aliases:
            pos = lowered.find(alias)
            if pos != -1 and pos < best_pos:
                best, best_pos = resource, pos
    return best


# A request to work around the security layer is classified, never answered with a
# clarification prompt: it must be blocked, audited, and counted against trajectory.
_BYPASS_ASK = re.compile(
    r"\b(disable|turn\s*off|switch\s*off|bypass|ignore|override|circumvent|get\s+around)\b"
    r"[\w\s,'-]{0,30}?\b(aegis|security|rules?|polic\w+|safety|guardrails?|restrictions?)\b")

# Exfiltration of sensitive material, with or without a named table.
_SENSITIVE_EXFIL = re.compile(
    r"\b(sensitive|credential|password|secret|api\s*keys?|token)s?\b"
    r"[\w\s,'-]{0,30}?\b|"
    r"\b(export|download|dump|exfiltrate|send|share|extract)\b[\w\s,'-]{0,30}?"
    r"\b(sensitive|credential|password|secret|api\s*keys?|tokens?)\b")

# Only a genuine conjunction makes a message compound. Without this, an item whose
# NAME contains a verb ("Remove the task Write tests") looks like two requests.
_CONJUNCTION = re.compile(r"\s+(and|then|also|after that|;)\s+|,\s*then\s+")

MULTI_INTENT_REPLY = (
    "That asks for more than one thing at once. Tell me one at a time so I can "
    "check each properly — I will not pick one for you.")

AMBIGUOUS_TARGET_REPLY = (
    "I need to know what to act on before I do anything. Name the project, task or "
    "file — for example “Delete the project Portfolio”. I will not guess "
    "a target for a destructive action.")

CONVERSATIONAL_REPLY = (
    "I can help you manage your projects, tasks and files. Try "
    "“Create a project called Megathon”, “Show me my projects”, "
    "or “Delete the project Portfolio”.")


def plan(user_request: str) -> dict:
    """Turn a natural-language request into a single proposed tool call.

    Returns action "none" when the message is conversation rather than a request to
    do something. Proposing an action for every utterance is how a greeting ends up
    reading a production table.
    """
    text = (user_request or "").strip()
    lowered = text.lower()
    op = infer_op_class(text)
    workspace = _workspace_target(text)
    everything = bool(re.search(r"\b(all|every|everything|entire)\b", lowered))
    # ------------------------------------------ security-relevant asks come first
    # These must be classified before the conversational guard, or a bypass
    # request with no action verb would be answered with small talk.
    if _BYPASS_ASK.search(lowered):
        return {"action": "disable_security", "resource": "", "parameters": {}}
    if _SENSITIVE_EXFIL.search(lowered):
        return {"action": "export_sensitive", "resource": "", "parameters": {}}
    if re.search(r"\b(another|other)\s+user('s)?\s+(data|files?|projects?|account)", lowered):
        return {"action": "access_other_user_data", "resource": "users", "parameters": {}}
    if re.search(r"\b(make|grant|give)\s+(me|myself)\s+(an?\s+)?(admin|root)", lowered):
        return {"action": "escalate_privilege", "resource": "", "parameters": {}}
    if re.search(r"\b(delete|clear|wipe)\s+(the\s+)?(audit|logs?)\b", lowered):
        return {"action": "modify_audit_log", "resource": "audit_demo", "parameters": {}}

    # Catch-all: anything the injection detector flags is a request to work around
    # the security layer. It must be classified and blocked, never answered with a
    # clarification, or the attempt never reaches the audit log or trajectory.
    if injection.scan(text)["detected"]:
        return {"action": "disable_security", "resource": "", "parameters": {}}

    # A compound instruction has more than one thing to do. Silently acting on one
    # clause is a guess; ask which one instead.
    if _CONJUNCTION.search(lowered) and _distinct_ops(text) > 1:
        return {"action": "none", "resource": "", "parameters": {},
                "reply": MULTI_INTENT_REPLY}


    # No operation verb and nothing actionable named -> the user is talking, not
    # asking for work. Proposing an action for every utterance is how a greeting
    # ends up reading a production table.
    if op is None and workspace is None and not _names_a_resource(text):
        return {"action": "none", "resource": "", "parameters": {},
                "reply": CONVERSATIONAL_REPLY}
    if op is None:
        op = OP_READ

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

    # ------------------------------------------------------------- legacy data plane
    resource = _resource_from(text)

    if resource is None:
        # The user named an operation but nothing to perform it on.
        return {"action": "none", "resource": "", "parameters": {},
                "reply": AMBIGUOUS_TARGET_REPLY}

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
