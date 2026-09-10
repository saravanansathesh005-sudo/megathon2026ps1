"""Terms & Conditions for a general-purpose AI agent.

Classifies every proposed action into one of four bands and states what the band
implies. The policy engine consumes this; it is never the whole decision.

    NORMAL      permitted work                      -> ALLOW by default
    RISKY       meaningful consequences             -> REQUIRE_CONFIRMATION by default
    PRIVILEGED  destructive / high impact           -> evaluated on full context
    FORBIDDEN   never executes, whoever asks        -> BLOCK, non-overridable
"""

from __future__ import annotations

from app.security.registry import (
    FORBIDDEN, NORMAL, PRIVILEGED, RISKY, category_of, is_known,
)

# What each band means, in words a person can read.
BAND_MEANING = {
    NORMAL: "routine permitted work",
    RISKY: "meaningful consequences; the user must confirm",
    PRIVILEGED: "destructive or high-impact; decided on the full security context",
    FORBIDDEN: "never permitted, regardless of who asks",
}

# Escalation applied by context rather than by the action name alone.
_ESCALATION_ORDER = [NORMAL, RISKY, PRIVILEGED, FORBIDDEN]


def _raise_to(current: str, target: str) -> str:
    return target if _ESCALATION_ORDER.index(target) > _ESCALATION_ORDER.index(current) else current


def classify(action_name: str, resource: dict, affected_records: int,
             total_records: int, injection: dict | None = None) -> dict:
    """Return the T&C band for this action in this context, with reasons."""
    reasons: list[str] = []

    if not is_known(action_name):
        return {
            "category": FORBIDDEN,
            "meaning": BAND_MEANING[FORBIDDEN],
            "reasons": ["action '" + str(action_name) + "' is not in the registry"],
            "base_category": FORBIDDEN,
            "escalated": False,
        }

    base = category_of(action_name)
    category = base
    reasons.append("registry category " + base)

    # A request that tries to talk its way past the security layer is forbidden work,
    # whatever action the planner eventually proposed.
    if injection and injection.get("detected"):
        category = _raise_to(category, FORBIDDEN)
        reasons.append("request attempts to bypass or disable security controls")

    # Context raises the band; it never lowers it.
    if category != FORBIDDEN:
        if resource.get("is_production") and base in (RISKY, PRIVILEGED):
            category = _raise_to(category, PRIVILEGED)
            reasons.append("target is a production resource")
        if resource.get("is_sensitive") and base in (RISKY, PRIVILEGED):
            category = _raise_to(category, PRIVILEGED)
            reasons.append("target holds sensitive data")
        # "delete one project" is RISKY; "delete every project" is not.
        if base == RISKY and total_records and affected_records >= max(10, total_records * 0.5):
            category = _raise_to(category, PRIVILEGED)
            reasons.append("operation spans " + str(affected_records) + " of "
                           + str(total_records) + " records")

    return {
        "category": category,
        "meaning": BAND_MEANING[category],
        "reasons": reasons,
        "base_category": base,
        "escalated": category != base,
    }
