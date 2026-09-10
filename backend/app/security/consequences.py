"""Structured consequence analysis. No prose generation."""

from __future__ import annotations

from app.security.registry import ACTIONS, OP_DELETE, OP_DROP, OP_EXPORT, OP_WRITE, is_known


def analyse(action_name: str, resource: dict, deps: dict, affected_records: int,
            total_records: int) -> dict:
    if not is_known(action_name):
        return {"direct": ["unknown action"], "indirect": [], "data_sensitivity": "unknown",
                "resource_criticality": "unknown", "service_impact": [],
                "affected_resource_count": 0, "affected_records": 0, "total_records": 0}

    op = ACTIONS[action_name].op_class
    name = resource.get("name", "?")
    direct: list[str] = []

    if op == OP_DROP:
        direct.append(f"resource '{name}' removed entirely ({total_records} records)")
    elif op == OP_DELETE:
        direct.append(f"{affected_records} of {total_records} records deleted from '{name}'")
    elif op == OP_WRITE:
        direct.append(f"{affected_records} records written in '{name}'")
    elif op == OP_EXPORT:
        direct.append(f"{affected_records} records leave the system boundary from '{name}'")
    else:
        direct.append(f"{affected_records} records read from '{name}'")

    if resource.get("is_sensitive"):
        direct.append("sensitive data involved")
    if resource.get("is_production"):
        direct.append("production resource")

    indirect = [f"dependent resource '{d}' affected" for d in deps.get("all", [])]
    service_impact = deps.get("all", [])

    return {
        "direct": direct,
        "indirect": indirect,
        "data_sensitivity": "sensitive" if resource.get("is_sensitive") else "normal",
        "resource_criticality": resource.get("criticality", "low"),
        "service_impact": service_impact,
        "affected_resource_count": 1 + len(service_impact),
        "affected_records": affected_records,
        "total_records": total_records,
    }
