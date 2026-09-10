"""Unified action analysis. One object, produced once, consumed by API, UI and executor."""

from __future__ import annotations

import hashlib
import json
import re

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Record, Resource
from app.security import (
    authorization, blast_radius, consequences, dependencies, injection as injection_mod,
    intent as intent_mod, invariants as invariants_mod, policy, reversibility, terms as terms_mod,
    trajectory,
)
from app.security.identity import Identity
from app.security.registry import ACTIONS, OP_DELETE, OP_DROP, OP_EXPORT, is_known


def action_hash(action_name: str, resource_name: str, parameters: dict) -> str:
    canonical = json.dumps(
        {"action": action_name, "resource": resource_name, "parameters": parameters},
        sort_keys=True, separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def resource_dict(resource: Resource | None, name: str) -> dict:
    if resource is None:
        return {"name": name, "exists": False, "is_production": False, "is_sensitive": False,
                "criticality": "low", "is_disposable": False, "kind": "unknown"}
    return {
        "name": resource.name, "exists": True, "kind": resource.kind,
        "is_production": resource.is_production, "is_sensitive": resource.is_sensitive,
        "criticality": resource.criticality, "is_disposable": resource.is_disposable,
        "dropped": resource.dropped,
    }


def _owner_filter(query, resource: Resource, owner_user_id: int | None):
    """Restrict to rows this principal may reach. Shared resources have no owner."""
    if owner_user_id is None:
        return query
    return query.where(
        (Record.owner_user_id == owner_user_id) | (Record.owner_user_id.is_(None)))


def _record_counts(db: Session, resource: Resource | None, action_name: str,
                   parameters: dict, owner_user_id: int | None = None) -> tuple[int, int]:
    """Measure the real target set. Never guess from the action category."""
    if resource is None:
        return 0, 0
    total = db.scalar(_owner_filter(
        select(func.count(Record.id)).where(Record.resource_id == resource.id),
        resource, owner_user_id)) or 0

    if not is_known(action_name):
        return 0, total
    op = ACTIONS[action_name].op_class

    if op == OP_DROP:
        return total, total
    if op in (OP_DELETE, OP_EXPORT):
        filt = parameters.get("filter", "all")
        if filt in ("all", "*", None):
            return total, total
        rows = db.scalars(_owner_filter(
            select(Record).where(Record.resource_id == resource.id),
            resource, owner_user_id)).all()
        matched = sum(1 for r in rows if _matches(r.payload, filt))
        return matched, total
    if op == "write":
        return int(parameters.get("count", 1)), total
    return total, total  # reads touch everything they return


def _matches(payload: dict, filt) -> bool:
    if isinstance(filt, dict):
        return all(str(payload.get(k)) == str(v) for k, v in filt.items())
    return False


def _instruction_only(user_request: str, parameters: dict) -> str:
    """The user's instruction, with any payload submitted for review removed.

    Subtracting the payload string is unreliable - a planner re-emits code with
    different whitespace - so for a review request we keep only the text that
    introduces it: everything before the first fence or colon.
    """
    payload = parameters.get("code") or parameters.get("source")
    if not payload or not isinstance(payload, str):
        return user_request

    cut = len(user_request)
    for marker in ('```', ":"):
        at = user_request.find(marker)
        if at != -1:
            cut = min(cut, at)
    prefix = user_request[:cut].strip()

    # If there was no introducer at all, fall back to subtracting the payload.
    return prefix if prefix else user_request.replace(payload, ' ')


def analyse(db: Session, identity: Identity, user_request: str, action_name: str,
            resource_name: str, parameters: dict | None = None,
            approval_present: bool = False) -> dict:
    parameters = parameters or {}
    resource = db.scalar(select(Resource).where(Resource.name == resource_name))
    res = resource_dict(resource, resource_name)

    auth = authorization.check(identity.role, action_name)
    intent = intent_mod.check(user_request, action_name, resource_name, identity.role)
    deps = dependencies.dependents_of(db, resource_name)
    affected, total = _record_counts(db, resource, action_name, parameters,
                                     owner_user_id=identity.user_id)
    rev = reversibility.classify(action_name, res)
    cons = consequences.analyse(action_name, res, deps, affected, total)
    blast = blast_radius.compute(action_name, res, deps, affected, total, rev["level"])
    # Injection detection reads the user's INSTRUCTION, not data they submitted for
    # inspection. Code pasted for review is evidence, not intent: a payload inside it
    # must become a finding, not a refusal to look at the file. The instruction text
    # around it is still scanned, so "review this and disable security" still blocks.
    inject = injection_mod.scan(_instruction_only(user_request, parameters))
    tc = terms_mod.classify(action_name, res, affected, total, inject)
    traj = trajectory.analyse(db, identity.user_id, identity.role, action_name, resource_name)
    inv = invariants_mod.evaluate(identity.role, action_name, res, auth["authorized"],
                                  rev["level"], approval_present)
    verdict = policy.decide(
        authorization=auth, intent=intent, blast=blast, reversibility=rev,
        trajectory=traj, invariants=inv, resource=res, terms=tc, injection=inject,
        approval_present=approval_present, confirmation_present=approval_present,
    )

    return {
        "action": {"name": action_name, "resource": resource_name, "parameters": parameters,
                   "known": is_known(action_name),
                   "hash": action_hash(action_name, resource_name, parameters)},
        "identity": {"user": identity.username, "user_id": identity.user_id,
                     "role": identity.role, "agent": identity.agent_id,
                     "session": identity.session_id},
        "user_request": user_request,
        "resource": res,
        "authorization": auth,
        "intent": intent,
        "dependencies": deps,
        "consequences": cons,
        "blast_radius": blast,
        "reversibility": rev,
        "trajectory": traj,
        "safety_invariants": inv,
        "terms": tc,
        "injection": inject,
        "policy_decision": verdict,
    }
