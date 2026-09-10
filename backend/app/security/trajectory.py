"""Cross-session behavioural trajectory. Uses stored history, not just this request."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Action
from app.security.registry import ACTIONS, OP_SEVERITY, is_known, role_max_severity

NORMAL, ELEVATED, HIGH, CRITICAL, EXTREME = (
    "NORMAL", "ELEVATED", "HIGH", "CRITICAL", "EXTREME")

HISTORY_LIMIT = 50


def level_of(score: int) -> str:
    if score <= 3:
        return NORMAL
    if score <= 7:
        return ELEVATED
    if score <= 11:
        return HIGH
    if score <= 15:
        return CRITICAL
    return EXTREME


def analyse(db: Session, user_id: int, role: str, action_name: str,
            resource_name: str) -> dict:
    history = list(db.scalars(
        select(Action).where(Action.user_id == user_id)
        .order_by(Action.created_at.desc(), Action.id.desc()).limit(HISTORY_LIMIT)
    ).all())
    history.reverse()  # oldest first

    signals: list[str] = []
    score = 0

    denied = [a for a in history if a.decision == "BLOCK" or not a.authorized]
    if denied:
        pts = min(6, 2 * len(denied))
        score += pts
        signals.append(str(len(denied)) + " denied/blocked action(s) (+" + str(pts) + ")")

    max_sev = role_max_severity(role)
    escalations = [
        a for a in history
        if is_known(a.action_name) and OP_SEVERITY[ACTIONS[a.action_name].op_class] > max_sev
    ]
    if escalations:
        pts = min(6, 3 * len(escalations))
        score += pts
        signals.append(str(len(escalations)) + " privilege-escalation attempt(s) (+" + str(pts) + ")")

    expansions = [a for a in history if a.intent_status in ("SCOPE_EXPANSION", "OUT_OF_SCOPE")]
    if expansions:
        pts = min(6, 2 * len(expansions))
        score += pts
        signals.append(str(len(expansions)) + " scope-expansion event(s) (+" + str(pts) + ")")

    resources = {a.resource_name for a in history if a.resource_name}
    if resource_name:
        resources.add(resource_name)
    if len(resources) >= 3:
        score += 2
        signals.append(str(len(resources)) + " distinct resources touched (+2)")

    high_blast = [a for a in history if (a.blast_radius or 0) >= 5.0]
    if len(high_blast) >= 2:
        score += 3
        signals.append(str(len(high_blast)) + " high-blast-radius actions (+3)")

    if is_known(action_name):
        current_sev = OP_SEVERITY[ACTIONS[action_name].op_class]
        started_safe = (
            bool(history)
            and is_known(history[0].action_name)
            and OP_SEVERITY[ACTIONS[history[0].action_name].op_class] == 0
        )
        if started_safe and current_sev >= 3:
            score += 5
            signals.append("safe-to-destructive transition (+5)")

    sessions = {a.session_id for a in history if a.session_id}
    if len(sessions) >= 2 and (denied or escalations):
        score += 2
        signals.append("suspicious behaviour spanning " + str(len(sessions)) + " sessions (+2)")

    score = min(20, score)
    return {
        "score": score,
        "level": level_of(score),
        "signals": signals or ["no adverse history"],
        "history_size": len(history),
        "sessions_seen": len(sessions),
    }
