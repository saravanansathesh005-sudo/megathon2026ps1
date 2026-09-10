"""Unit tests for the deterministic security components."""

from __future__ import annotations

import pytest

from app.security import authorization, blast_radius, intent, invariants, policy, reversibility
from app.security.registry import ACTIONS, is_known

PROD_CRITICAL = {"name": "users", "is_production": True, "is_sensitive": True,
                 "criticality": "critical", "is_disposable": False}
TEST_TABLE = {"name": "test_table", "is_production": False, "is_sensitive": False,
              "criticality": "low", "is_disposable": True}
NO_DEPS = {"all": [], "direct": [], "transitive": [], "count": 0}
THREE_DEPS = {"all": ["orders", "audit_demo", "mock_files"], "direct": ["orders"],
              "transitive": ["audit_demo", "mock_files"], "count": 3}


# ----------------------------------------------------------------- authorization

@pytest.mark.parametrize("role,action,expected", [
    ("viewer", "read_table", True),
    ("viewer", "delete_records", False),
    ("viewer", "drop_table", False),
    ("editor", "update_record", True),
    ("editor", "delete_records", False),
    ("admin", "drop_table", True),
    ("admin", "send_email", True),
    ("security_admin", "read_table", True),
    ("security_admin", "drop_table", False),
])
def test_rbac(role, action, expected):
    assert authorization.check(role, action)["authorized"] is expected


def test_unknown_action_denied():
    result = authorization.check("admin", "rm_minus_rf")
    assert result["authorized"] is False
    assert "unknown action" in result["reason"]
    assert not is_known("rm_minus_rf")


# ------------------------------------------------------------------------ intent

def test_intent_within_scope():
    assert intent.check("Show me users", "read_table", "users", "viewer")["status"] == "WITHIN_SCOPE"


def test_intent_out_of_scope_severity_jump():
    result = intent.check("Update John's email", "delete_records", "users", "admin")
    assert result["status"] == "OUT_OF_SCOPE"


def test_intent_clean_test_data_is_within_scope():
    result = intent.check("Clean the disposable test table", "delete_records",
                          "test_table", "admin")
    assert result["status"] == "WITHIN_SCOPE"


def test_intent_scope_expansion():
    result = intent.check("Show me users", "insert_record", "users", "editor")
    assert result["status"] == "SCOPE_EXPANSION"


def test_intent_blocked_by_role_envelope():
    """A viewer asking to delete is outside the sanctioned envelope of the role."""
    result = intent.check("Delete all users", "delete_records", "users", "viewer")
    assert result["status"] == "OUT_OF_SCOPE"


def test_intent_resource_mismatch():
    result = intent.check("Show me orders", "read_table", "users", "viewer")
    assert result["status"] == "OUT_OF_SCOPE"


# ----------------------------------------------------------------- reversibility

@pytest.mark.parametrize("action,expected", [
    ("read_table", "R0"),
    ("list_tables", "R0"),
    ("insert_record", "R1"),
    ("update_record", "R1"),
    ("delete_records", "R2"),
    ("drop_table", "R3"),
    ("send_email", "R3"),
])
def test_reversibility_levels(action, expected):
    assert reversibility.classify(action, TEST_TABLE)["level"] == expected


def test_production_raises_r2_to_r3():
    assert reversibility.classify("delete_records", PROD_CRITICAL)["level"] == "R3"


def test_unknown_action_is_irreversible():
    assert reversibility.classify("mystery")["level"] == "R3"


# ----------------------------------------------------------------- blast radius

def test_blast_read_is_low():
    result = blast_radius.compute("read_table", PROD_CRITICAL, THREE_DEPS, 24, 24, "R0")
    assert result["score"] < 2.5
    assert result["severity"] == "LOW"


def test_blast_drop_production_is_critical():
    result = blast_radius.compute("drop_table", PROD_CRITICAL, THREE_DEPS, 24, 24, "R3")
    assert result["score"] >= 9.0
    assert result["severity"] == "CRITICAL"
    assert "production resource" in result["reasons"]


def test_blast_delete_test_table_is_moderate():
    result = blast_radius.compute("delete_records", TEST_TABLE, NO_DEPS, 12, 12, "R2")
    assert 2.5 <= result["score"] < 5.0
    assert result["severity"] == "MODERATE"


def test_blast_scales_with_record_scope():
    few = blast_radius.compute("delete_records", TEST_TABLE, NO_DEPS, 1, 100, "R2")["score"]
    many = blast_radius.compute("delete_records", TEST_TABLE, NO_DEPS, 100, 100, "R2")["score"]
    assert many > few, "blast radius must reflect the measured target set"


def test_blast_scales_with_dependencies():
    alone = blast_radius.compute("delete_records", PROD_CRITICAL, NO_DEPS, 10, 10, "R2")["score"]
    linked = blast_radius.compute("delete_records", PROD_CRITICAL, THREE_DEPS, 10, 10, "R2")["score"]
    assert linked > alone


def test_blast_is_deterministic():
    args = ("drop_table", PROD_CRITICAL, THREE_DEPS, 24, 24, "R3")
    assert blast_radius.compute(*args) == blast_radius.compute(*args)


# -------------------------------------------------------------------- invariants

def test_inv001_viewer_privileged_action():
    result = invariants.evaluate("viewer", "drop_table", PROD_CRITICAL, False, "R3", False)
    assert "INV-001" in [v["code"] for v in result["violations"]]


def test_inv002_unknown_action():
    result = invariants.evaluate("admin", "rm_minus_rf", PROD_CRITICAL, False, "R3", False)
    assert [v["code"] for v in result["violations"]] == ["INV-002"]


def test_inv003_production_destructive_by_editor():
    result = invariants.evaluate("editor", "delete_records", PROD_CRITICAL, False, "R3", False)
    assert "INV-003" in [v["code"] for v in result["violations"]]


def test_inv004_r3_without_approval():
    result = invariants.evaluate("admin", "drop_table", TEST_TABLE, True, "R3", False)
    assert "INV-004" in [v["code"] for v in result["violations"]]


def test_inv004_satisfied_with_approval():
    result = invariants.evaluate("admin", "drop_table", TEST_TABLE, True, "R3", True)
    assert "INV-004" not in [v["code"] for v in result["violations"]]


# ------------------------------------------------------------------ policy engine

def _terms(category="NORMAL"):
    return {"category": category, "meaning": "", "reasons": [],
            "base_category": category, "escalated": False}


def _ctx(**over):
    base = dict(
        authorization={"authorized": True, "reason": "ok"},
        intent={"status": "WITHIN_SCOPE", "reason": "ok"},
        blast={"score": 1.0, "severity": "LOW", "reasons": []},
        reversibility={"level": "R0", "rollback_supported": False, "explanation": ""},
        trajectory={"score": 0, "level": "NORMAL", "signals": []},
        invariants={"violations": [], "passed": True},
        resource=TEST_TABLE,
        terms=_terms(),
        injection={"detected": False, "signals": [], "count": 0},
    )
    base.update(over)
    return base


def test_policy_allows_safe_read():
    assert policy.decide(**_ctx())["decision"] == policy.ALLOW


def test_policy_blocks_on_authorization():
    result = policy.decide(**_ctx(authorization={"authorized": False, "reason": "denied"}))
    assert result["decision"] == policy.BLOCK


def test_policy_blocks_out_of_scope():
    result = policy.decide(**_ctx(intent={"status": "OUT_OF_SCOPE", "reason": "too far"}))
    assert result["decision"] == policy.BLOCK


def test_policy_blocks_on_invariant():
    result = policy.decide(**_ctx(invariants={
        "violations": [{"code": "INV-003", "title": "t", "detail": "prod", "passed": False}],
        "passed": False}))
    assert result["decision"] == policy.BLOCK
    assert any("INV-003" in r for r in result["reasons"])


def test_policy_privileged_production_requires_confirmation():
    """A privileged production action is never silently allowed."""
    result = policy.decide(**_ctx(
        terms=_terms("PRIVILEGED"),
        blast={"score": 7.1, "severity": "HIGH", "reasons": []},
        reversibility={"level": "R3", "rollback_supported": True, "explanation": ""},
        resource=PROD_CRITICAL))
    assert result["decision"] == policy.REQUIRE_CONFIRMATION


def test_policy_blocks_privileged_action_with_very_high_blast():
    result = policy.decide(**_ctx(
        terms=_terms("PRIVILEGED"),
        blast={"score": 8.7, "severity": "CRITICAL", "reasons": []},
        reversibility={"level": "R3", "rollback_supported": True, "explanation": ""},
        resource=PROD_CRITICAL))
    assert result["decision"] == policy.BLOCK


def test_policy_blocks_at_absolute_blast_ceiling():
    result = policy.decide(**_ctx(blast={"score": 9.8, "severity": "CRITICAL", "reasons": []}))
    assert result["decision"] == policy.BLOCK


def test_policy_forbidden_band_is_blocked():
    result = policy.decide(**_ctx(terms=_terms("FORBIDDEN")))
    assert result["decision"] == policy.BLOCK


def test_policy_risky_band_requires_confirmation():
    result = policy.decide(**_ctx(terms=_terms("RISKY")))
    assert result["decision"] == policy.REQUIRE_CONFIRMATION


def test_policy_never_returns_admin_approval():
    """The decision set is exactly three values; no human approval state exists."""
    for category in ("NORMAL", "RISKY", "PRIVILEGED", "FORBIDDEN"):
        for score in (0, 9, 13, 19):
            out = policy.decide(**_ctx(
                terms=_terms(category),
                trajectory={"score": score, "level": "X", "signals": []}))
            assert out["decision"] in policy.DECISIONS
            assert out["requires_human_approval"] is False


def test_policy_requires_confirmation_for_r2():
    result = policy.decide(**_ctx(
        reversibility={"level": "R2", "rollback_supported": True, "explanation": ""}))
    assert result["decision"] == policy.REQUIRE_CONFIRMATION


def test_policy_trajectory_escalates_one_level():
    calm = policy.decide(**_ctx())["decision"]
    hot = policy.decide(**_ctx(trajectory={"score": 9, "level": "HIGH", "signals": []}))
    assert calm == policy.ALLOW
    assert hot["decision"] == policy.REQUIRE_CONFIRMATION
    assert hot["escalated_by"]


def test_policy_trajectory_critical_escalates_risky_to_block():
    result = policy.decide(**_ctx(
        terms=_terms("RISKY"),
        trajectory={"score": 13, "level": "CRITICAL", "signals": []}))
    assert result["decision"] == policy.BLOCK


def test_policy_trajectory_extreme_blocks_risky_work():
    result = policy.decide(**_ctx(
        terms=_terms("RISKY"),
        trajectory={"score": 18, "level": "EXTREME", "signals": []}))
    assert result["decision"] == policy.BLOCK


def test_policy_trajectory_never_blocks_routine_permitted_work():
    """Trajectory is behavioural risk, not permission: a safe read is slowed, not refused."""
    result = policy.decide(**_ctx(
        terms=_terms("NORMAL"),
        trajectory={"score": 20, "level": "EXTREME", "signals": []}))
    assert result["decision"] == policy.REQUIRE_CONFIRMATION


def test_policy_trajectory_only_restricts():
    """Escalation can never relax a decision."""
    for category in ("NORMAL", "RISKY", "PRIVILEGED"):
        calm = policy.decide(**_ctx(terms=_terms(category)))
        for score in (8, 12, 16, 20):
            hot = policy.decide(**_ctx(
                terms=_terms(category),
                trajectory={"score": score, "level": "X", "signals": []}))
            assert policy.RANK[hot["decision"]] >= policy.RANK[calm["decision"]]


def test_policy_trajectory_cannot_unblock():
    blocked = policy.decide(**_ctx(
        authorization={"authorized": False, "reason": "denied"},
        trajectory={"score": 0, "level": "NORMAL", "signals": []}))
    assert blocked["decision"] == policy.BLOCK


def test_policy_is_pure():
    ctx = _ctx()
    assert policy.decide(**ctx) == policy.decide(**ctx)


def test_policy_always_explains():
    for ctx in (_ctx(), _ctx(authorization={"authorized": False, "reason": "denied"})):
        assert policy.decide(**ctx)["reasons"]


def test_every_registered_action_has_a_spec():
    for name, spec in ACTIONS.items():
        assert spec.name == name
        assert spec.reversibility in ("R0", "R1", "R2", "R3")
