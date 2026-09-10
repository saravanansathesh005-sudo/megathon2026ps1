"""Reversibility classification."""

from __future__ import annotations

from app.security.registry import ACTIONS, R3, REVERSIBILITY_LABEL, is_known


def classify(action_name: str, resource: dict | None = None) -> dict:
    if not is_known(action_name):
        return {"level": R3, "explanation": "unknown action treated as irreversible",
                "rollback_supported": False}
    spec = ACTIONS[action_name]
    level, rollback = spec.reversibility, spec.rollback_supported
    explanation = REVERSIBILITY_LABEL[level]

    # Production raises the real-world cost of undoing a destructive action.
    if resource and resource.get("is_production") and level == "R2":
        level, explanation = R3, "compensatable in principle, but irreversible in production"
    return {"level": level, "explanation": explanation, "rollback_supported": rollback}
