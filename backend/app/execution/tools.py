"""Allowlisted mock tools. No arbitrary SQL, no shell, no filesystem."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Record, Resource


class ToolError(RuntimeError):
    pass


def _resource(db: Session, name: str) -> Resource:
    resource = db.scalar(select(Resource).where(Resource.name == name))
    if resource is None:
        raise ToolError("unknown resource: " + str(name))
    return resource


def _count(db: Session, resource: Resource) -> int:
    return db.scalar(select(func.count(Record.id)).where(Record.resource_id == resource.id)) or 0


def _matches(payload: dict, filt) -> bool:
    if isinstance(filt, dict):
        return all(str(payload.get(k)) == str(v) for k, v in filt.items())
    return False


def list_tables(db: Session, resource_name: str, params: dict) -> dict:
    rows = db.scalars(select(Resource).where(Resource.dropped == False)).all()  # noqa: E712
    return {"tables": [r.name for r in rows], "count": len(rows)}


def read_table(db: Session, resource_name: str, params: dict) -> dict:
    resource = _resource(db, resource_name)
    limit = int(params.get("limit", 10))
    rows = db.scalars(
        select(Record).where(Record.resource_id == resource.id).limit(limit)).all()
    return {"resource": resource_name, "rows": [r.payload for r in rows],
            "returned": len(rows), "total": _count(db, resource)}


def insert_record(db: Session, resource_name: str, params: dict) -> dict:
    resource = _resource(db, resource_name)
    payload = params.get("payload") or {"value": "new"}
    db.add(Record(resource_id=resource.id, payload=payload))
    db.flush()
    return {"resource": resource_name, "inserted": 1, "total": _count(db, resource)}


def update_record(db: Session, resource_name: str, params: dict) -> dict:
    resource = _resource(db, resource_name)
    filt = params.get("filter", {})
    changes = params.get("changes", {})
    rows = db.scalars(select(Record).where(Record.resource_id == resource.id)).all()
    updated = 0
    for row in rows:
        if _matches(row.payload, filt):
            merged = dict(row.payload)
            merged.update(changes)
            row.payload = merged
            updated += 1
    db.flush()
    return {"resource": resource_name, "updated": updated, "total": _count(db, resource)}


def export_data(db: Session, resource_name: str, params: dict) -> dict:
    resource = _resource(db, resource_name)
    rows = db.scalars(select(Record).where(Record.resource_id == resource.id)).all()
    return {"resource": resource_name, "exported": len(rows),
            "destination": params.get("destination", "mock://export")}


def send_email(db: Session, resource_name: str, params: dict) -> dict:
    mailbox = _resource(db, "mock_email")
    db.add(Record(resource_id=mailbox.id, payload={
        "to": params.get("to", "someone@example.com"),
        "subject": params.get("subject", "(no subject)"),
        "body": params.get("body", ""),
    }))
    db.flush()
    return {"sent": 1, "to": params.get("to", "someone@example.com")}


def delete_records(db: Session, resource_name: str, params: dict) -> dict:
    resource = _resource(db, resource_name)
    filt = params.get("filter", "all")
    rows = db.scalars(select(Record).where(Record.resource_id == resource.id)).all()
    deleted = 0
    for row in rows:
        if filt in ("all", "*", None) or _matches(row.payload, filt):
            db.delete(row)
            deleted += 1
    db.flush()
    return {"resource": resource_name, "deleted": deleted, "remaining": _count(db, resource)}


def drop_table(db: Session, resource_name: str, params: dict) -> dict:
    resource = _resource(db, resource_name)
    rows = db.scalars(select(Record).where(Record.resource_id == resource.id)).all()
    for row in rows:
        db.delete(row)
    resource.dropped = True
    db.flush()
    return {"resource": resource_name, "dropped": True, "records_removed": len(rows),
            "remaining": _count(db, resource)}


TOOLS = {
    "list_tables": list_tables,
    "read_table": read_table,
    "insert_record": insert_record,
    "update_record": update_record,
    "export_data": export_data,
    "send_email": send_email,
    "delete_records": delete_records,
    "drop_table": drop_table,
}


def invoke(db: Session, action_name: str, resource_name: str, params: dict) -> dict:
    tool = TOOLS.get(action_name)
    if tool is None:
        raise ToolError("tool not allowlisted: " + str(action_name))
    return tool(db, resource_name, params or {})
