"""Prompt-injection / security-bypass detection on the raw user request.

This is a *signal*, never a control. It raises the Terms & Conditions band and feeds
trajectory. Every other layer still runs. A request that evades this detector is still
evaluated by authorization, intent, blast radius, reversibility and invariants.

User input is always untrusted, including input that claims otherwise.
"""

from __future__ import annotations

import re

# Phrases whose only purpose is to talk past the security layer.
PATTERNS: list[tuple[str, str]] = [
    (r"\bignore\s+(your|the|all|any)?\s*(previous\s+)?(security\s+)?(rules?|instructions?|polic\w+)",
     "asks the agent to ignore its rules"),
    (r"\b(disable|turn\s+off|switch\s+off|bypass|circumvent|evade|get\s+around)\s+"
     r"(aegis|security|the\s+guard|protection|safeguards?|controls?)",
     "asks to disable or bypass security"),
    (r"\b(act|behave|pretend|pose)\s+as\s+(an?\s+)?(admin|administrator|root|superuser|security)",
     "asks the agent to impersonate a privileged role"),
    (r"\b(i\s+am|i'm)\s+(an?\s+)?(admin|administrator|root|superuser|the\s+owner)\b",
     "asserts a privileged role in the request body"),
    (r"\bassume\s+(that\s+)?(i\s+have|you\s+have|we\s+have)\s+(permission|access|authorisation|authorization)",
     "asks the agent to assume authorization"),
    (r"\b(do\s*n[o']?t|no\s+need\s+to|skip|without)\s+(ask(ing)?|require|prompt(ing)?|request(ing)?)"
     r"\s*(me\s+)?(for\s+)?(a\s+)?(confirmation|approval|permission)",
     "asks to skip confirmation"),
    (r"\boverride\s+(the\s+)?(previous\s+)?(security\s+)?(polic\w+|decision|rules?|block)",
     "asks to override policy"),
    (r"\b(grant|give)\s+(me|myself|us)\s+(admin|root|full|elevated)\s*(access|rights|privileges?)?",
     "asks for a privilege grant"),
    (r"\b(delete|erase|wipe|clear)\s+(the\s+)?(audit|log|logs|history|trail)\b",
     "asks to tamper with audit records"),
    (r"\byou\s+are\s+now\s+(in\s+)?(developer|debug|god|unrestricted)\s+mode",
     "claims a privileged operating mode"),
]

_COMPILED = [(re.compile(p, re.IGNORECASE), label) for p, label in PATTERNS]


def scan(user_request: str) -> dict:
    """Return {detected, signals[], count} for a raw request string."""
    text = user_request or ""
    signals = [label for rx, label in _COMPILED if rx.search(text)]
    return {
        "detected": bool(signals),
        "signals": signals,
        "count": len(signals),
    }
