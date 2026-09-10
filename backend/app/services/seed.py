"""Small deterministic demo dataset."""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import (
    Action, ActionEvent, ApprovalRequest, Conversation, Message, Record, Resource,
    ResourceDependency, SecurityRestriction, Snapshot, User, UserSession,
)
from app.security.identity import hash_password

USERS = [
    ("viewer", "viewer123", "viewer", "Val Viewer"),
    ("editor", "editor123", "editor", "Eddie Editor"),
    ("user", "user123", "user", "Uma User"),
    ("user2", "user2123", "user", "Ravi Second"),
    ("admin", "admin123", "admin", "Ada Admin"),
    ("secadmin", "secadmin123", "security_admin", "Sam Security"),
]

RESOURCES = [
    # name, kind, production, sensitive, criticality, disposable, rows
    ("users", "table", True, True, "critical", False, 24),
    ("orders", "table", True, False, "high", False, 18),
    ("test_table", "table", False, False, "low", True, 12),
    ("audit_demo", "table", False, False, "medium", False, 10),
    ("mock_email", "service", False, True, "medium", False, 3),
    ("mock_files", "store", False, False, "low", False, 8),
    # Workspace resources for the general agent. Owned per user, not production.
    ("projects", "workspace", False, False, "medium", False, 0),
    ("tasks", "workspace", False, False, "low", False, 0),
    ("files", "workspace", False, False, "low", False, 0),
]

# Per-user starter workspace: (resource, [names])
WORKSPACE = {
    "projects": ["Megathon", "Portfolio", "Thesis"],
    "tasks": ["Draft slides", "Write tests", "Book travel"],
    "files": ["notes.md", "budget.csv"],
}

# (dependent, depends_on) - dependent breaks if depends_on is damaged.
DEPENDENCIES = [
    ("orders", "users"),
    ("audit_demo", "orders"),
    ("mock_files", "users"),
]


def reset(db: Session) -> dict:
    for model in (ActionEvent, Snapshot, ApprovalRequest, Action, Message, Conversation,
                  SecurityRestriction, Record, ResourceDependency, Resource,
                  UserSession, User):
        db.execute(delete(model))
    db.flush()

    for username, password, role, display in USERS:
        db.add(User(username=username, password_hash=hash_password(password),
                    role=role, display_name=display))

    resources: dict[str, Resource] = {}
    for name, kind, prod, sensitive, criticality, disposable, rows in RESOURCES:
        resource = Resource(name=name, kind=kind, is_production=prod, is_sensitive=sensitive,
                            criticality=criticality, is_disposable=disposable)
        db.add(resource)
        db.flush()
        resources[name] = resource
        for i in range(1, rows + 1):
            db.add(Record(resource_id=resource.id,
                          payload={"id": str(i), "value": name + "-" + str(i)}))

    for dependent, depends_on in DEPENDENCIES:
        db.add(ResourceDependency(dependent_id=resources[dependent].id,
                                  depends_on_id=resources[depends_on].id))

    # Give every non-observer account its own isolated starter workspace.
    db.flush()
    workspace_rows = 0
    for user in db.scalars(select(User)).all():
        if user.role in ("security_admin",):
            continue
        for resource_name, names in WORKSPACE.items():
            for index, name in enumerate(names, start=1):
                db.add(Record(resource_id=resources[resource_name].id,
                              owner_user_id=user.id,
                              payload={"id": str(index), "name": name, "value": name}))
                workspace_rows += 1

    db.commit()
    return {"users": len(USERS), "resources": len(RESOURCES),
            "dependencies": len(DEPENDENCIES),
            "records": sum(r[6] for r in RESOURCES) + workspace_rows}


def ensure_seeded(db: Session) -> None:
    if db.scalar(select(User).limit(1)) is None:
        reset(db)
