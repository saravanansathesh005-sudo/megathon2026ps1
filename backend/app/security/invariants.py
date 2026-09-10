"""Hard safety constraints. The policy engine may not casually override these."""

from __future__ import annotations

from app.security.registry import ACTIONS, OP_SEVERITY, is_known, role_max_severity

INVARIANTS = {
    "INV-001": "Under-privileged identity cannot perform privileged actions",
    "INV-002": "Unknown actions cannot execute",
    "INV-003": "Production destructive actions require elevated protection",
    "INV-004": "R3 actions cannot silently execute",
    "INV-005": "Agent cannot bypass AEGIS",
    "INV-006": "Approval must match user, session and action",
    "INV-007": "Expired approval cannot execute",
    "INV-008": "Tampered audit chain must be detectable",
}

DESTRUCTIVE_SEVERITY = OP_SEVERITY["delete"]


def violation(code: str, detail: str) -> dict:
    return {"code": code, "title": INVARIANTS[code], "detail": detail, "passed": False}


def evaluate(role: str, action_name: str, resource: dict, authorized: bool,
             reversibility_level: str, approval_present: bool) -> dict:
    violations: list[dict] = []

    if not is_known(action_name):
        violations.append(violation("INV-002", action_name + " is not in the action registry"))
        return {"violations": violations, "passed": False, "checked": ["INV-002"]}

    severity = OP_SEVERITY[ACTIONS[action_name].op_class]

    if not authorized and severity > role_max_severity(role):
        violations.append(violation(
            "INV-001",
            "role " + role + " attempted " + action_name + " above its privilege ceiling"))

    if severity >= DESTRUCTIVE_SEVERITY and resource.get("is_production") \
            and role not in ("admin", "security_admin"):
        violations.append(violation(
            "INV-003",
            "destructive action on production resource " + str(resource.get("name"))
            + " by role " + role))

    if reversibility_level == "R3" and not approval_present:
        violations.append(violation(
            "INV-004", action_name + " is R3 and carries no human approval"))

    return {
        "violations": violations,
        "passed": not violations,
        "checked": ["INV-001", "INV-002", "INV-003", "INV-004"],
    }
