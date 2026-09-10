"""Deterministic policy engine - the central security authority.

Pure function. Same inputs, same decision, every time. No ML on this path.
"""

from __future__ import annotations

ALLOW = "ALLOW"
REQUIRE_CONFIRMATION = "REQUIRE_CONFIRMATION"
REQUIRE_ADMIN_APPROVAL = "REQUIRE_ADMIN_APPROVAL"
BLOCK = "BLOCK"

RANK = {ALLOW: 0, REQUIRE_CONFIRMATION: 1, REQUIRE_ADMIN_APPROVAL: 2, BLOCK: 3}


def escalate(decision: str) -> str:
    if decision == ALLOW:
        return REQUIRE_CONFIRMATION
    if decision == REQUIRE_CONFIRMATION:
        return REQUIRE_ADMIN_APPROVAL
    return decision


def decide(*, authorization: dict, intent: dict, blast: dict, reversibility: dict,
           trajectory: dict, invariants: dict, resource: dict,
           approval_present: bool = False) -> dict:
    """Return the single authoritative decision plus the reasons behind it."""
    reasons: list[str] = []

    # --- Hard blocks. INV-004 is satisfied by requiring approval, not by blocking.
    hard = [v for v in invariants["violations"] if v["code"] != "INV-004"]
    if hard:
        for item in hard:
            reasons.append("safety invariant " + item["code"] + " failed: " + item["detail"])
        return {"decision": BLOCK, "reasons": reasons, "escalated_by": []}

    if not authorization["authorized"]:
        reasons.append("authorization denied: " + authorization["reason"])
        return {"decision": BLOCK, "reasons": reasons, "escalated_by": []}

    if intent["status"] == "OUT_OF_SCOPE":
        reasons.append("intent out of scope: " + intent["reason"])
        return {"decision": BLOCK, "reasons": reasons, "escalated_by": []}

    if trajectory["score"] >= 16:
        reasons.append("trajectory " + str(trajectory["score"]) + "/20 ("
                       + trajectory["level"] + ") - behaviour rejected")
        return {"decision": BLOCK, "reasons": reasons, "escalated_by": []}

    # --- Graded decision
    decision = ALLOW
    level = reversibility["level"]
    score = blast["score"]

    if level == "R3" and resource.get("is_production"):
        decision = REQUIRE_ADMIN_APPROVAL
        reasons.append(level + " irreversible action on a production resource")
    elif score >= 7.5:
        decision = REQUIRE_ADMIN_APPROVAL
        reasons.append("blast radius " + str(score) + "/10 (" + blast["severity"] + ")")
    elif level == "R3":
        decision = REQUIRE_CONFIRMATION
        reasons.append(level + " irreversible action")
    elif score >= 4.5 or level == "R2" or intent["status"] == "SCOPE_EXPANSION":
        decision = REQUIRE_CONFIRMATION
        if score >= 4.5:
            reasons.append("blast radius " + str(score) + "/10 (" + blast["severity"] + ")")
        if level == "R2":
            reasons.append(level + " action requires a restorable snapshot")
        if intent["status"] == "SCOPE_EXPANSION":
            reasons.append("intent scope expansion: " + intent["reason"])

    escalated_by: list[str] = []
    traj = trajectory["score"]
    if traj >= 12:
        decision = escalate(escalate(decision))
        escalated_by.append("trajectory " + str(traj) + "/20 (" + trajectory["level"] + ")")
    elif traj >= 8:
        decision = escalate(decision)
        escalated_by.append("trajectory " + str(traj) + "/20 (" + trajectory["level"] + ")")

    if decision == ALLOW and not reasons:
        reasons.append("within scope, low impact (blast radius " + str(score) + "/10)")
    reasons.extend(escalated_by)

    return {"decision": decision, "reasons": reasons, "escalated_by": escalated_by}
