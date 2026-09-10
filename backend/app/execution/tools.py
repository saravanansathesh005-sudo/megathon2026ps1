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


# ----------------------------------------------------------- workspace domain tools
# These operate on the same Record store, scoped by owner_user_id, so blast radius,
# snapshots, verification and rollback all work unchanged.

def _owned(db: Session, resource: Resource, owner: int | None):
    q = select(Record).where(Record.resource_id == resource.id)
    if owner is not None:
        q = q.where((Record.owner_user_id == owner) | (Record.owner_user_id.is_(None)))
    return db.scalars(q).all()


def _create_item(db: Session, resource_name: str, params: dict, label: str) -> dict:
    resource = _resource(db, resource_name)
    owner = params.get("_owner_user_id")
    name = params.get("name") or params.get("title") or ("untitled " + label)
    rows = _owned(db, resource, owner)
    new_id = str(max([int(r.payload.get("id", 0)) for r in rows] or [0]) + 1)
    db.add(Record(resource_id=resource.id, owner_user_id=owner,
                  payload={"id": new_id, "name": name, "value": name}))
    db.flush()
    return {"resource": resource_name, "created": 1, "id": new_id, "name": name,
            "total": _count(db, resource)}


def _delete_item(db: Session, resource_name: str, params: dict, label: str) -> dict:
    resource = _resource(db, resource_name)
    owner = params.get("_owner_user_id")
    target = params.get("name") or params.get("id")
    if target is None:
        # Deleting "one" item requires knowing which one. Never fall back to all.
        raise ToolError("no " + label + " named; refusing to delete without a target")
    deleted = 0
    for row in _owned(db, resource, owner):
        if target is None or str(row.payload.get("name")) == str(target)                 or str(row.payload.get("id")) == str(target):
            db.delete(row)
            deleted += 1
            if target is not None:
                break
    db.flush()
    return {"resource": resource_name, "deleted": deleted, "target": target,
            "remaining": len(_owned(db, resource, owner))}


def create_project(db, r, p): return _create_item(db, "projects", p, "project")
def create_task(db, r, p): return _create_item(db, "tasks", p, "task")
def create_file(db, r, p): return _create_item(db, "files", p, "file")
def delete_project(db, r, p): return _delete_item(db, "projects", p, "project")
def delete_task(db, r, p): return _delete_item(db, "tasks", p, "task")
def delete_file(db, r, p): return _delete_item(db, "files", p, "file")


def _list_items(db: Session, resource_name: str, params: dict) -> dict:
    resource = _resource(db, resource_name)
    rows = _owned(db, resource, params.get("_owner_user_id"))
    return {"resource": resource_name, "items": [r.payload for r in rows],
            "count": len(rows)}


def list_projects(db, r, p): return _list_items(db, "projects", p)
def list_tasks(db, r, p): return _list_items(db, "tasks", p)
def list_files(db, r, p): return _list_items(db, "files", p)
def read_project(db, r, p): return _list_items(db, "projects", p)
def read_file(db, r, p): return _list_items(db, "files", p)


def _update_item(db: Session, resource_name: str, params: dict) -> dict:
    resource = _resource(db, resource_name)
    target = params.get("name") or params.get("id")
    changes = params.get("changes") or {}
    updated = 0
    for row in _owned(db, resource, params.get("_owner_user_id")):
        if target is None or str(row.payload.get("name")) == str(target)                 or str(row.payload.get("id")) == str(target):
            merged = dict(row.payload)
            merged.update(changes)
            row.payload = merged
            updated += 1
    db.flush()
    return {"resource": resource_name, "updated": updated}


def update_project(db, r, p): return _update_item(db, "projects", p)
def update_task(db, r, p): return _update_item(db, "tasks", p)


def analyse_code(db: Session, resource_name: str, params: dict) -> dict:
    """Report risks in submitted Python. Reads nothing, writes nothing, runs nothing."""
    from app.agent import code_review

    code = params.get("code") or params.get("source") or ""
    if not str(code).strip():
        raise ToolError("no code supplied to analyse")
    return code_review.review(str(code))


def calculate(db: Session, resource_name: str, params: dict) -> dict:
    return {"expression": params.get("expression", ""), "note": "evaluated by the agent"}


def move_files(db: Session, resource_name: str, params: dict) -> dict:
    return _update_item(db, "files", {**params, "changes": {"folder": params.get("to", "/")}})


def bulk_update(db: Session, resource_name: str, params: dict) -> dict:
    return _update_item(db, resource_name or "projects", {**params, "name": None})


def update_config(db: Session, resource_name: str, params: dict) -> dict:
    return {"config_updated": True, "keys": sorted((params.get("changes") or {}).keys())}


def delete_all_projects(db: Session, resource_name: str, params: dict) -> dict:
    resource = _resource(db, "projects")
    rows = _owned(db, resource, params.get("_owner_user_id"))
    for row in rows:
        db.delete(row)
    db.flush()
    return {"resource": "projects", "deleted": len(rows), "remaining": _count(db, resource)}


def export_sensitive(db: Session, resource_name: str, params: dict) -> dict:
    raise ToolError("export_sensitive has no executable implementation by design")


TOOLS = {
    "create_project": create_project, "read_project": read_project,
    "list_projects": list_projects, "update_project": update_project,
    "create_task": create_task, "list_tasks": list_tasks, "update_task": update_task,
    "create_file": create_file, "read_file": read_file, "list_files": list_files,
    "calculate": calculate,
    "analyse_code": analyse_code,
    "delete_project": delete_project, "delete_task": delete_task, "delete_file": delete_file,
    "move_files": move_files, "bulk_update": bulk_update, "update_config": update_config,
    "delete_all_projects": delete_all_projects,
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
