"""Deterministic blast radius, 0-10. Measured, not guessed."""

from __future__ import annotations

from app.security.registry import (
    ACTIONS, OP_DELETE, OP_DROP, OP_EXPORT, OP_READ, OP_WRITE, REVERSIBILITY_WEIGHT, is_known,
)

# Base severity of the operation itself, normalised 0..1.
OP_BASE = {OP_READ: 0.05, OP_WRITE: 0.30, OP_EXPORT: 0.45, OP_DELETE: 0.72, OP_DROP: 1.0}
CRITICALITY = {"low": 0.25, "medium": 0.5, "high": 0.75, "critical": 1.0}

W_PROD, W_SENS, W_CRIT, W_DEPS, W_SCOPE, W_REV = 0.28, 0.18, 0.18, 0.13, 0.13, 0.10

LOW, MODERATE, HIGH, CRITICAL = "LOW", "MODERATE", "HIGH", "CRITICAL"


def severity_of(score: float) -> str:
    if score < 2.5:
        return LOW
    if score < 5.0:
        return MODERATE
    if score < 7.5:
        return HIGH
    return CRITICAL


def compute(action_name: str, resource: dict, deps: dict, affected_records: int,
            total_records: int, reversibility_level: str) -> dict:
    if not is_known(action_name):
        return {"score": 10.0, "severity": CRITICAL, "reasons": ["unknown action"],
                "affected_resources": [], "components": {}}

    base = OP_BASE[ACTIONS[action_name].op_class]
    dep_count = deps.get("count", 0)
    scope = (affected_records / total_records) if total_records else 0.0
    scope = max(0.0, min(1.0, scope))

    c_prod = 1.0 if resource.get("is_production") else 0.0
    c_sens = 1.0 if resource.get("is_sensitive") else 0.0
    c_crit = CRITICALITY.get(resource.get("criticality", "low"), 0.25)
    c_deps = min(1.0, dep_count / 4.0)
    c_rev = REVERSIBILITY_WEIGHT.get(reversibility_level, 0.0)

    context = (W_PROD * c_prod + W_SENS * c_sens + W_CRIT * c_crit
               + W_DEPS * c_deps + W_SCOPE * scope + W_REV * c_rev)

    score = round(min(10.0, 10.0 * base * (0.5 + 0.5 * context)), 1)

    reasons = [f"operation base severity {base:.2f}"]
    if c_prod:
        reasons.append("production resource")
    if c_sens:
        reasons.append("sensitive data")
    if c_crit >= 0.75:
        reasons.append(f"criticality {resource.get('criticality')}")
    if dep_count:
        reasons.append(f"{dep_count} dependent resource(s)")
    if scope >= 0.9 and affected_records:
        reasons.append(f"affects all {affected_records} records")
    elif affected_records:
        reasons.append(f"affects {affected_records} of {total_records} records")
    if c_rev >= 0.66:
        reasons.append(f"reversibility {reversibility_level}")

    return {
        "score": score,
        "severity": severity_of(score),
        "reasons": reasons,
        "affected_resources": [resource.get("name")] + deps.get("all", []),
        "components": {
            "base": round(base, 3), "production": c_prod, "sensitive": c_sens,
            "criticality": c_crit, "dependents": round(c_deps, 3),
            "record_scope": round(scope, 3), "reversibility": c_rev,
            "context": round(context, 3),
        },
    }
