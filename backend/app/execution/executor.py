"""Controlled execution: snapshot -> execute -> verify -> commit / rollback.

Nothing reaches a tool except through here, and only with a fresh policy decision.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.execution import tools
from app.logging_config import utc_now
from app.models import Action, Record, Resource, Snapshot
from app.security.registry import ACTIONS, OP_DELETE, OP_DROP, OP_READ, is_known
from app.services import audit

VERIFIED, VERIFICATION_FAILED, NOT_VERIFIED = "VERIFIED", "VERIFICATION_FAILED", "not_verified"

# Actions whose post-execution row count is exactly predictable.
BULK_DELETE_ACTIONS = {"delete_records"}


def _resource_counts(db: Session) -> dict[str, int]:
    rows = db.execute(
        select(Resource.name, func.count(Record.id))
        .select_from(Resource).outerjoin(Record, Record.resource_id == Resource.id)
        .group_by(Resource.name)
    ).all()
    return {name: count for name, count in rows}


def take_snapshot(db: Session, action: Action) -> Snapshot | None:
    resource = db.scalar(select(Resource).where(Resource.name == action.resource_name))
    if resource is None:
        return None
    rows = db.scalars(select(Record).where(Record.resource_id == resource.id)).all()
    snapshot = Snapshot(
        action_id=action.id, resource_name=resource.name, created_at=utc_now(),
        state={"records": [{"id": r.id, "payload": r.payload} for r in rows],
               "dropped": resource.dropped},
    )
    db.add(snapshot)
    db.flush()
    return snapshot


def restore_snapshot(db: Session, snapshot: Snapshot) -> dict:
    resource = db.scalar(select(Resource).where(Resource.name == snapshot.resource_name))
    if resource is None:
        return {"restored": False, "reason": "resource missing"}
    for row in db.scalars(select(Record).where(Record.resource_id == resource.id)).all():
        db.delete(row)
    db.flush()
    for item in snapshot.state.get("records", []):
        db.add(Record(id=item["id"], resource_id=resource.id, payload=item["payload"]))
    resource.dropped = snapshot.state.get("dropped", False)
    snapshot.restored = True
    db.flush()
    return {"restored": True, "records": len(snapshot.state.get("records", []))}


def expected_outcome(db: Session, action: Action, before: dict[str, int]) -> dict:
    name, params = action.action_name, action.parameters or {}
    target = action.resource_name
    start = before.get(target, 0)
    if not is_known(name):
        return {}
    op = ACTIONS[name].op_class
    if op == OP_DROP:
        return {"target_count": 0, "mutates": True}
    if op == OP_DELETE:
        # Only the bulk actions take a filter; an item delete removes a named row and
        # leaves the rest, so its exact post-count is not predictable here.
        if name not in BULK_DELETE_ACTIONS:
            return {"target_count": None, "mutates": True}
        filt = params.get("filter", "all")
        if filt in ("all", "*", None):
            return {"target_count": 0, "mutates": True}
        return {"target_count": None, "mutates": True}
    if op == OP_READ:
        return {"target_count": start, "mutates": False}
    return {"target_count": None, "mutates": True}


def verify(db: Session, action: Action, before: dict[str, int], expected: dict) -> dict:
    after = _resource_counts(db)
    target = action.resource_name
    problems: list[str] = []

    for name, count in before.items():
        if name != target and after.get(name, 0) != count:
            problems.append("unexpected change in '" + name + "': "
                            + str(count) + " -> " + str(after.get(name, 0)))

    expected_count = expected.get("target_count")
    if expected_count is not None and after.get(target, 0) != expected_count:
        problems.append("'" + str(target) + "' expected " + str(expected_count)
                        + " records, found " + str(after.get(target, 0)))

    if not expected.get("mutates", True) and after.get(target, 0) != before.get(target, 0):
        problems.append("read-only action changed '" + str(target) + "'")

    if (action.parameters or {}).get("_demo_force_verify_fail"):
        problems.append("demo: forced verification failure")

    return {
        "status": VERIFIED if not problems else VERIFICATION_FAILED,
        "problems": problems,
        "before": before,
        "after": after,
        "expected": expected,
    }


def execute(db: Session, action: Action, *, snapshot_required: bool) -> dict:
    """Run the action under snapshot/verify/commit-or-rollback control."""
    before = _resource_counts(db)
    expected = expected_outcome(db, action, before)

    snapshot = take_snapshot(db, action) if snapshot_required else None
    if snapshot:
        audit.record(db, event_type="snapshot.created", action_id=action.id,
                     username=action.username, agent_id=action.agent_id,
                     session_id=action.session_id, action_name=action.action_name,
                     resource_name=action.resource_name,
                     detail={"snapshot_id": snapshot.id,
                             "records": len(snapshot.state.get("records", []))})

    try:
        result = tools.invoke(db, action.action_name, action.resource_name,
                              action.parameters or {})
        action.execution_status = "executed"
    except tools.ToolError as exc:
        action.execution_status = "failed"
        action.verification_status = NOT_VERIFIED
        action.commit_status = "aborted"
        action.result = {"error": str(exc)}
        audit.record(db, event_type="execution.failed", action_id=action.id,
                     username=action.username, agent_id=action.agent_id,
                     session_id=action.session_id, action_name=action.action_name,
                     resource_name=action.resource_name, detail={"error": str(exc)})
        return {"execution_status": "failed", "error": str(exc),
                "verification": None, "commit_status": "aborted", "rollback_status": "none"}

    verification = verify(db, action, before, expected)
    action.verification_status = verification["status"]

    if verification["status"] == VERIFIED:
        action.commit_status = "committed"
        rollback_status = "none"
        db.commit()
        audit.record(db, event_type="execution.committed", action_id=action.id,
                     username=action.username, agent_id=action.agent_id,
                     session_id=action.session_id, action_name=action.action_name,
                     resource_name=action.resource_name, decision="COMMIT",
                     detail={"result": result, "verification": verification["status"]})
        db.commit()
    else:
        if snapshot is not None:
            restore_snapshot(db, snapshot)
            rollback_status = "rolled_back"
        else:
            rollback_status = "unavailable"
        action.commit_status = "rolled_back" if snapshot else "not_committed"
        db.commit()
        audit.record(db, event_type="execution.rolled_back", action_id=action.id,
                     username=action.username, agent_id=action.agent_id,
                     session_id=action.session_id, action_name=action.action_name,
                     resource_name=action.resource_name, decision="ROLLBACK",
                     detail={"problems": verification["problems"],
                             "rollback_status": rollback_status})
        db.commit()

    action.result = {"tool_result": result, "verification": verification}
    db.commit()

    return {
        "execution_status": action.execution_status,
        "tool_result": result,
        "verification": verification,
        "commit_status": action.commit_status,
        "rollback_status": rollback_status,
        "snapshot_id": snapshot.id if snapshot else None,
    }
