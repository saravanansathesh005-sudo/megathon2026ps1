"""Action registry, RBAC map, reversibility classes. Single source of truth.

Every action carries a Terms & Conditions category (see security/terms.py):
    NORMAL      permitted by default
    RISKY       meaningful consequences, default REQUIRE_CONFIRMATION
    PRIVILEGED  destructive / high impact, evaluated on full context
    FORBIDDEN   never executes, whoever asks
"""

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

# Terms & Conditions categories.
NORMAL, RISKY, PRIVILEGED, FORBIDDEN = "NORMAL", "RISKY", "PRIVILEGED", "FORBIDDEN"


@dataclass(frozen=True)
class ActionSpec:
    name: str
    op_class: str
    reversibility: str
    mutates: bool
    rollback_supported: bool
    description: str
    category: str = NORMAL
    # Canonical resource this action always operates on. None = caller names the
    # resource (the legacy table-oriented actions).
    resource: str | None = None


ACTIONS: dict[str, ActionSpec] = {
    # ---------------------------------------------------------------- legacy data plane
    "list_tables": ActionSpec("list_tables", OP_READ, R0, False, False, "List resources", NORMAL),
    "read_table": ActionSpec("read_table", OP_READ, R0, False, False, "Read rows", NORMAL),
    "insert_record": ActionSpec("insert_record", OP_WRITE, R1, True, True, "Insert a row", NORMAL),
    "update_record": ActionSpec("update_record", OP_WRITE, R1, True, True, "Update rows", NORMAL),
    "export_data": ActionSpec("export_data", OP_EXPORT, R2, False, False,
                              "Export rows out of the system", RISKY),
    "send_email": ActionSpec("send_email", OP_EXPORT, R3, True, False,
                             "Send an external email", PRIVILEGED, "mock_email"),
    "delete_records": ActionSpec("delete_records", OP_DELETE, R2, True, True,
                                 "Delete rows", PRIVILEGED),
    "drop_table": ActionSpec("drop_table", OP_DROP, R3, True, True,
                             "Drop an entire resource", PRIVILEGED),

    # ------------------------------------------------------------------ A. NORMAL work
    "create_project": ActionSpec("create_project", OP_WRITE, R1, True, True,
                                 "Create a project", NORMAL, "projects"),
    "read_project": ActionSpec("read_project", OP_READ, R0, False, False,
                               "Read one project", NORMAL, "projects"),
    "list_projects": ActionSpec("list_projects", OP_READ, R0, False, False,
                                "List projects", NORMAL, "projects"),
    "update_project": ActionSpec("update_project", OP_WRITE, R1, True, True,
                                 "Update a project", NORMAL, "projects"),
    "create_task": ActionSpec("create_task", OP_WRITE, R1, True, True, "Create a task", NORMAL, "tasks"),
    "list_tasks": ActionSpec("list_tasks", OP_READ, R0, False, False, "List tasks", NORMAL, "tasks"),
    "update_task": ActionSpec("update_task", OP_WRITE, R1, True, True, "Update a task", NORMAL, "tasks"),
    "create_file": ActionSpec("create_file", OP_WRITE, R1, True, True, "Create a file", NORMAL, "files"),
    "read_file": ActionSpec("read_file", OP_READ, R0, False, False, "Read a file", NORMAL, "files"),
    "list_files": ActionSpec("list_files", OP_READ, R0, False, False, "List files", NORMAL, "files"),
    "calculate": ActionSpec("calculate", OP_READ, R0, False, False,
                            "Perform a calculation", NORMAL),

    # -------------------------------------------------------------------- B. RISKY work
    "delete_project": ActionSpec("delete_project", OP_DELETE, R2, True, True,
                                 "Delete one project", RISKY, "projects"),
    "delete_task": ActionSpec("delete_task", OP_DELETE, R2, True, True,
                              "Delete one task", RISKY, "tasks"),
    "delete_file": ActionSpec("delete_file", OP_DELETE, R2, True, True,
                              "Delete one file", RISKY, "files"),
    "move_files": ActionSpec("move_files", OP_WRITE, R2, True, True,
                             "Move many files", RISKY, "files"),
    "bulk_update": ActionSpec("bulk_update", OP_WRITE, R2, True, True,
                              "Large batch update", RISKY),
    "update_config": ActionSpec("update_config", OP_WRITE, R2, True, True,
                                "Modify important configuration", RISKY),

    # ------------------------------------------------- C. PRIVILEGED / DESTRUCTIVE work
    "delete_all_projects": ActionSpec("delete_all_projects", OP_DELETE, R3, True, True,
                                      "Delete every project", PRIVILEGED, "projects"),
    "export_sensitive": ActionSpec("export_sensitive", OP_EXPORT, R3, False, False,
                                   "Export sensitive information", PRIVILEGED),
    "update_permissions": ActionSpec("update_permissions", OP_WRITE, R3, True, False,
                                     "Modify access control", PRIVILEGED),
    "update_security_settings": ActionSpec("update_security_settings", OP_WRITE, R3, True, False,
                                           "Modify security configuration", PRIVILEGED),

    # ------------------------------------------------------------------- D. FORBIDDEN
    # Registered so a proposal for one is named and audited, never merely "unknown".
    "disable_security": ActionSpec("disable_security", OP_DROP, R3, True, False,
                                   "Disable AEGIS", FORBIDDEN),
    "modify_audit_log": ActionSpec("modify_audit_log", OP_WRITE, R3, True, False,
                                   "Alter audit records", FORBIDDEN),
    "escalate_privilege": ActionSpec("escalate_privilege", OP_WRITE, R3, True, False,
                                     "Grant self additional privileges", FORBIDDEN),
    "access_other_user_data": ActionSpec("access_other_user_data", OP_EXPORT, R3, False, False,
                                         "Read another user's protected data", FORBIDDEN),
}

ROLES = ("viewer", "editor", "user", "admin", "security_admin")

# Normal end-user workspace actions.
_USER_NORMAL = {
    "create_project", "read_project", "list_projects", "update_project",
    "create_task", "list_tasks", "update_task",
    "create_file", "read_file", "list_files", "calculate",
    "list_tables", "read_table",
}
_USER_RISKY = {"delete_project", "delete_task", "delete_file", "move_files",
               "bulk_update", "update_config", "export_data"}

RBAC: dict[str, set[str]] = {
    # Legacy demo roles - unchanged, existing tests depend on these exact sets.
    "viewer": {"list_tables", "read_table"},
    "editor": {"list_tables", "read_table", "insert_record", "update_record"},
    # Default role for an authenticated end user.
    "user": _USER_NORMAL | _USER_RISKY,
    "admin": {
        "list_tables", "read_table", "insert_record", "update_record",
        "export_data", "send_email", "delete_records", "drop_table",
    } | _USER_NORMAL | _USER_RISKY | {
        "delete_all_projects", "export_sensitive",
        "update_permissions", "update_security_settings",
    },
    # Security admin observes; it never mutates.
    "security_admin": {"list_tables", "read_table"},
}

# Roles permitted to read the Admin Security Terminal. Observability only.
OBSERVER_ROLES = {"admin", "security_admin"}

# Retained for backward compatibility with the legacy approval module. There is no
# administrator approval workflow: AEGIS decides automatically.
APPROVER_ROLES = OBSERVER_ROLES


def get_spec(action_name: str) -> ActionSpec | None:
    return ACTIONS.get(action_name)


def is_known(action_name: str) -> bool:
    return action_name in ACTIONS


def category_of(action_name: str) -> str:
    spec = ACTIONS.get(action_name)
    return spec.category if spec else FORBIDDEN


def role_max_severity(role: str) -> int:
    allowed = RBAC.get(role, set())
    if not allowed:
        return -1
    return max(OP_SEVERITY[ACTIONS[a].op_class] for a in allowed)


def role_allows(role: str, action_name: str) -> bool:
    return action_name in RBAC.get(role, set())
