"""Deterministic policy engine - the central security authority.

Pure function. Same inputs, same decision, every time. No ML on this path, and no
human in it: AEGIS resolves every action automatically to exactly one of three
verdicts. There is no administrator approval state.

Priority, highest first:
    unknown action            -> BLOCK
    hard invariant failure    -> BLOCK
    authorization failure     -> BLOCK
    out of scope              -> BLOCK
    forbidden T&C band        -> BLOCK
    privileged / destructive  -> evaluated on full context
    action risk band          -> ALLOW / REQUIRE_CONFIRMATION / BLOCK
    trajectory                -> may restrict further, never relax
"""

from __future__ import annotations

from app.security.registry import FORBIDDEN, NORMAL, PRIVILEGED, RISKY

ALLOW = "ALLOW"
REQUIRE_CONFIRMATION = "REQUIRE_CONFIRMATION"
BLOCK = "BLOCK"

DECISIONS = (ALLOW, REQUIRE_CONFIRMATION, BLOCK)
RANK = {ALLOW: 0, REQUIRE_CONFIRMATION: 1, BLOCK: 2}
_BY_RANK = {0: ALLOW, 1: REQUIRE_CONFIRMATION, 2: BLOCK}

# A privileged action whose measured impact reaches this is refused outright.
PRIVILEGED_BLOCK_BLAST = 8.5
# Any action this large is refused regardless of band.
ABSOLUTE_BLOCK_BLAST = 9.5
# Below this an ordinary action needs no confirmation.
CONFIRM_BLAST = 4.5


def escalate(decision: str, steps: int = 1, cap: str = BLOCK) -> str:
    """Raise restriction by `steps`, never past `cap`, never downwards."""
    target = min(RANK[decision] + max(0, steps), RANK[cap])
    return _BY_RANK[max(target, RANK[decision])]


def _trajectory_steps(score: int, category: str) -> int:
    if score >= 16:
        return 2
    if score >= 12:
        return 2 if category in (RISKY, PRIVILEGED) else 1
    if score >= 8:
        return 1
    return 0


def decide(*, authorization: dict, intent: dict, blast: dict, reversibility: dict,
           trajectory: dict, invariants: dict, resource: dict,
           terms: dict | None = None, injection: dict | None = None,
           file_risk: dict | None = None,
           approval_present: bool = False, confirmation_present: bool = False) -> dict:
    """Return the single authoritative decision plus the reasons behind it."""
    reasons: list[str] = []
    category = (terms or {}).get("category", NORMAL)

    # ------------------------------------------------------------------ hard blocks
    # INV-004 is satisfied by obtaining confirmation, not by refusing outright.
    hard = [v for v in invariants["violations"] if v["code"] != "INV-004"]
    if hard:
        for item in hard:
            reasons.append("safety invariant " + item["code"] + " failed: " + item["detail"])
        return _verdict(BLOCK, reasons, [], category)

    if not authorization["authorized"]:
        reasons.append("authorization denied: " + authorization["reason"])
        return _verdict(BLOCK, reasons, [], category)

    if intent["status"] == "OUT_OF_SCOPE":
        reasons.append("intent out of scope: " + intent["reason"])
        return _verdict(BLOCK, reasons, [], category)

    # A target that does not exist cannot be reasoned about. Refuse rather than
    # evaluate a phantom resource with default (low) risk attributes.
    if resource.get("name") and not resource.get("exists", True):
        reasons.append("there is no resource named '" + str(resource["name"]) + "'")
        return _verdict(BLOCK, reasons, [], category)

    # A file carrying a CRITICAL indicator is refused whatever the action's own
    # category is. The evidence comes from filescan, which reads bytes and never
    # executes anything, so this remains a deterministic check.
    if file_risk and file_risk.get("highest_severity") == "CRITICAL":
        for item in file_risk.get("findings", []):
            if item.get("severity") == "CRITICAL":
                reasons.append("file risk: " + item.get("title", "critical indicator"))
        return _verdict(BLOCK, reasons, [], category)

    if category == FORBIDDEN:
        for r in (terms or {}).get("reasons", []):
            reasons.append("terms & conditions: " + r)
        if injection and injection.get("detected"):
            for signal in injection["signals"]:
                reasons.append("security-bypass attempt: " + signal)
        return _verdict(BLOCK, reasons, [], category)

    score = blast["score"]
    level = reversibility["level"]

    if score >= ABSOLUTE_BLOCK_BLAST:
        reasons.append("blast radius " + str(score) + "/10 exceeds the maximum permitted impact")
        return _verdict(BLOCK, reasons, [], category)

    # -------------------------------------------------------------- graded decision
    decision = ALLOW

    if category == PRIVILEGED:
        if score >= PRIVILEGED_BLOCK_BLAST:
            decision = BLOCK
            reasons.append("privileged action with blast radius " + str(score) + "/10 ("
                           + blast["severity"] + ")")
        else:
            decision = REQUIRE_CONFIRMATION
            reasons.append("privileged or destructive action requires explicit confirmation")
            if level in ("R2", "R3"):
                reasons.append(level + " reversibility")
    elif category == RISKY:
        decision = REQUIRE_CONFIRMATION
        reasons.append("risky action with meaningful consequences")
        if score >= CONFIRM_BLAST:
            reasons.append("blast radius " + str(score) + "/10 (" + blast["severity"] + ")")
    else:  # NORMAL
        if score >= CONFIRM_BLAST or level in ("R2", "R3") \
                or intent["status"] == "SCOPE_EXPANSION":
            decision = REQUIRE_CONFIRMATION
            if score >= CONFIRM_BLAST:
                reasons.append("blast radius " + str(score) + "/10 (" + blast["severity"] + ")")
            if level in ("R2", "R3"):
                reasons.append(level + " action requires a restorable snapshot")
            if intent["status"] == "SCOPE_EXPANSION":
                reasons.append("intent scope expansion: " + intent["reason"])

    if file_risk and file_risk.get("highest_severity") == "HIGH" and decision == ALLOW:
        decision = REQUIRE_CONFIRMATION
        reasons.append("file carries HIGH severity risk indicators")

    # ------------------------------------------------------- trajectory: restrict only
    escalated_by: list[str] = []
    steps = _trajectory_steps(trajectory["score"], category)
    if steps:
        # Routine permitted work is never refused on behaviour alone; it is slowed down.
        cap = REQUIRE_CONFIRMATION if category == NORMAL else BLOCK
        raised = escalate(decision, steps, cap)
        if raised != decision:
            escalated_by.append("trajectory " + str(trajectory["score"]) + "/20 ("
                                + trajectory["level"] + ")")
            decision = raised

    if decision == ALLOW and not reasons:
        reasons.append("permitted work, within scope, low impact (blast radius "
                       + str(score) + "/10)")
    reasons.extend(escalated_by)
    return _verdict(decision, reasons, escalated_by, category)


def _verdict(decision: str, reasons: list[str], escalated_by: list[str],
             category: str) -> dict:
    return {
        "decision": decision,
        "reasons": reasons,
        "escalated_by": escalated_by,
        "terms_category": category,
        "requires_human_approval": False,
    }
