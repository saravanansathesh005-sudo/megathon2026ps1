"""RBAC: can this identity ever perform this action?"""

from __future__ import annotations

from app.security.registry import RBAC, is_known, role_allows


def check(role: str, action_name: str) -> dict:
    if not is_known(action_name):
        return {"authorized": False, "reason": f"unknown action '{action_name}'",
                "role": role, "permitted_actions": sorted(RBAC.get(role, set()))}
    if not role_allows(role, action_name):
        return {"authorized": False, "reason": f"role '{role}' may not perform '{action_name}'",
                "role": role, "permitted_actions": sorted(RBAC.get(role, set()))}
    return {"authorized": True, "reason": f"role '{role}' permits '{action_name}'",
            "role": role, "permitted_actions": sorted(RBAC.get(role, set()))}
