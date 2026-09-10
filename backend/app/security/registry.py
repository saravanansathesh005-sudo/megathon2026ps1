"""Action registry, RBAC map, reversibility classes. Single source of truth."""

from __future__ import annotations

from dataclasses import dataclass

# Operation classes ordered by severity.
OP_READ, OP_WRITE, OP_EXPORT, OP_DELETE, OP_DROP = "read", "write", "export", "delete", "drop"
OP_SEVERITY = {OP_READ: 0, OP_WRITE: 1, OP_EXPORT: 2, OP_DELETE: 3, OP_DROP: 4}

# Reversibility classes.
R0, R1, R2, R3 = "R0", "R1", "R2", "R3"
REVERSIBILITY_WEIGHT = {R0: 0.0, R1: 0.33, R2: 0.66, R3: 1.0}
REVERSIBILITY_LABEL = {
    R0: "read-only, no state change",
    R1: "easily reversible",
    R2: "compensatable via snapshot restore",
    R3: "difficult or impossible to reverse",
}


@dataclass(frozen=True)
class ActionSpec:
    name: str
    op_class: str
    reversibility: str
    mutates: bool
    rollback_supported: bool
    description: str


ACTIONS: dict[str, ActionSpec] = {
    "list_tables": ActionSpec("list_tables", OP_READ, R0, False, False, "List resources"),
    "read_table": ActionSpec("read_table", OP_READ, R0, False, False, "Read rows"),
    "insert_record": ActionSpec("insert_record", OP_WRITE, R1, True, True, "Insert a row"),
    "update_record": ActionSpec("update_record", OP_WRITE, R1, True, True, "Update rows"),
    "export_data": ActionSpec("export_data", OP_EXPORT, R2, False, False, "Export rows out of the system"),
    "send_email": ActionSpec("send_email", OP_EXPORT, R3, True, False, "Send an external email"),
    "delete_records": ActionSpec("delete_records", OP_DELETE, R2, True, True, "Delete rows"),
    "drop_table": ActionSpec("drop_table", OP_DROP, R3, True, True, "Drop an entire resource"),
}

ROLES = ("viewer", "editor", "admin", "security_admin")

RBAC: dict[str, set[str]] = {
    "viewer": {"list_tables", "read_table"},
    "editor": {"list_tables", "read_table", "insert_record", "update_record"},
    "admin": {
        "list_tables", "read_table", "insert_record", "update_record",
        "export_data", "send_email", "delete_records", "drop_table",
    },
    # Security admin oversees; it approves rather than mutates.
    "security_admin": {"list_tables", "read_table"},
}

APPROVER_ROLES = {"admin", "security_admin"}


def get_spec(action_name: str) -> ActionSpec | None:
    return ACTIONS.get(action_name)


def is_known(action_name: str) -> bool:
    return action_name in ACTIONS


def role_max_severity(role: str) -> int:
    allowed = RBAC.get(role, set())
    if not allowed:
        return -1
    return max(OP_SEVERITY[ACTIONS[a].op_class] for a in allowed)


def role_allows(role: str, action_name: str) -> bool:
    return action_name in RBAC.get(role, set())
