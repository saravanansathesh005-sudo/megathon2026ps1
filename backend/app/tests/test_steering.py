"""Steering rules.

The property that matters most is the one asserted last and hardest: steering can
only restrict. If any test here shows a rules file relaxing a decision, the design
is broken, not the test.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.security import policy, steering as steering_mod
from app.security.steering import ALLOW, BLOCK, REQUIRE_CONFIRMATION, Steering


def build(text: str) -> Steering:
    import yaml

    s = Steering(status="active", path="test.yaml")
    steering_mod.parse(yaml.safe_load(text) or {}, s)
    s.status = "invalid" if s.errors else "active"
    return s


def check(s: Steering, **kw) -> dict:
    base = dict(action="read_table", resource="projects", role="user", blast=1.0,
                category="NORMAL", affected_records=1, trajectory_score=0)
    base.update(kw)
    return steering_mod.evaluate(s, **base)


# ------------------------------------------------------------------------- loading

def test_absent_file_applies_no_rules():
    s = steering_mod.load("does-not-exist-anywhere.yaml")

    assert s.status == "absent"
    assert check(s)["floor"] == ALLOW


def test_invalid_yaml_degrades_to_confirmation():
    s = Steering(status="invalid", path="x.yaml", errors=["bad"])
    result = check(s)

    assert result["floor"] == REQUIRE_CONFIRMATION
    assert "invalid" in result["reasons"][0]


def test_unknown_action_in_a_rule_is_an_error():
    s = build("never: [not_a_real_action]")

    assert s.status == "invalid"
    assert "not a registered action" in s.errors[0]


def test_unknown_rule_key_is_an_error():
    assert build("delete_everything: true").status == "invalid"


def test_every_error_is_collected_not_just_the_first():
    s = build("never: [nope_one, nope_two]\nmax_records_per_action: not_a_number")

    assert len(s.errors) == 3


def test_a_valid_file_loads_as_active():
    s = build("never: [export_sensitive]\nconfirm_when: {blast_radius_at_least: 4}")

    assert s.status == "active"
    assert s.errors == []


def test_the_shipped_example_file_is_valid():
    """The example in the repo must parse - it is what people copy."""
    s = steering_mod.load("aegis.steering.example.yaml")

    assert s.status == "active", s.errors
    assert s.rule_count() > 0


# --------------------------------------------------------------------------- rules

def test_never_blocks():
    s = build("never: [export_sensitive]")

    assert check(s, action="export_sensitive")["floor"] == BLOCK


def test_never_does_not_touch_other_actions():
    s = build("never: [export_sensitive]")

    assert check(s, action="read_table")["floor"] == ALLOW


def test_always_confirm_raises_to_confirmation():
    s = build("always_confirm: [update_config]")

    assert check(s, action="update_config")["floor"] == REQUIRE_CONFIRMATION


def test_blast_radius_block_threshold():
    s = build("block_when: {blast_radius_at_least: 8}")

    assert check(s, blast=8.0)["floor"] == BLOCK
    assert check(s, blast=7.9)["floor"] == ALLOW


def test_blast_radius_confirm_threshold():
    s = build("confirm_when: {blast_radius_at_least: 3.5}")

    assert check(s, blast=3.5)["floor"] == REQUIRE_CONFIRMATION
    assert check(s, blast=3.4)["floor"] == ALLOW


def test_record_ceiling_blocks_above_the_limit():
    s = build("max_records_per_action: 50")

    assert check(s, affected_records=51)["floor"] == BLOCK
    assert check(s, affected_records=50)["floor"] == ALLOW


def test_trajectory_ceiling_blocks():
    s = build("max_trajectory_score: 15")

    assert check(s, trajectory_score=16)["floor"] == BLOCK
    assert check(s, trajectory_score=15)["floor"] == ALLOW


def test_category_confirmation():
    s = build("confirm_categories: [RISKY]")

    assert check(s, category="RISKY")["floor"] == REQUIRE_CONFIRMATION
    assert check(s, category="NORMAL")["floor"] == ALLOW


def test_role_restriction_applies_only_to_that_role():
    s = build("roles:\n  user:\n    never: [drop_table]")

    assert check(s, action="drop_table", role="user")["floor"] == BLOCK
    assert check(s, action="drop_table", role="admin")["floor"] == ALLOW


def test_resource_restriction_applies_only_to_that_resource():
    s = build("resources:\n  users:\n    never: [delete_records]")

    assert check(s, action="delete_records", resource="users")["floor"] == BLOCK
    assert check(s, action="delete_records", resource="projects")["floor"] == ALLOW


def test_matched_rules_are_named():
    s = build("never: [export_sensitive]")

    assert check(s, action="export_sensitive")["matched"] == ["never"]


# ---------------------------------------------------------------------------- hours

def _at(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 9, 11, hour, minute, tzinfo=timezone.utc)


def test_inside_the_window_is_unrestricted():
    s = build('allowed_hours: {start: "09:00", end: "18:00", timezone: "+00:00"}')

    assert check(s, now=_at(12))["floor"] == ALLOW


def test_outside_the_window_confirms_by_default():
    s = build('allowed_hours: {start: "09:00", end: "18:00", timezone: "+00:00"}')

    assert check(s, now=_at(20))["floor"] == REQUIRE_CONFIRMATION


def test_outside_the_window_can_block():
    s = build('allowed_hours: {start: "09:00", end: "18:00", timezone: "+00:00",'
              ' outside: block}')

    assert check(s, now=_at(20))["floor"] == BLOCK


def test_the_offset_is_applied():
    # 05:00 UTC is 10:30 in +05:30, which is inside the window.
    s = build('allowed_hours: {start: "09:00", end: "18:00", timezone: "+05:30"}')

    assert check(s, now=_at(5))["floor"] == ALLOW
    assert check(s, now=_at(1))["floor"] == REQUIRE_CONFIRMATION


def test_a_window_crossing_midnight_works():
    s = build('allowed_hours: {start: "22:00", end: "06:00", timezone: "+00:00"}')

    assert check(s, now=_at(23))["floor"] == ALLOW
    assert check(s, now=_at(2))["floor"] == ALLOW
    assert check(s, now=_at(12))["floor"] == REQUIRE_CONFIRMATION


def test_malformed_hours_are_rejected():
    assert build('allowed_hours: {start: "9am", end: "6pm"}').status == "invalid"


# ------------------------------------------------- the property the design rests on

CLEAN = {"authorization": {"authorized": True, "reason": ""},
         "intent": {"status": "WITHIN_SCOPE", "reason": ""},
         "blast": {"score": 1.0, "severity": "low"},
         "reversibility": {"level": "R0"},
         "trajectory": {"score": 0, "level": "none"},
         "invariants": {"violations": []},
         "resource": {"name": "projects", "exists": True},
         "terms": {"category": "NORMAL", "reasons": []}}


def decide(steer=None, **over):
    args = {**CLEAN, **over}
    return policy.decide(**args, steering=steer)["decision"]


@pytest.mark.parametrize("floor", [ALLOW, REQUIRE_CONFIRMATION, BLOCK])
def test_steering_never_relaxes_a_blocked_decision(floor):
    """A BLOCK stays a BLOCK, whatever the rules file says."""
    blocked = {"invariants": {"violations": [
        {"code": "INV-001", "detail": "agent identity missing"}]}}
    steer = {"floor": floor, "reasons": ["rule"], "matched": ["r"], "status": "active"}

    assert decide(steer, **blocked) == BLOCK


def test_steering_cannot_turn_a_forbidden_action_into_an_allow():
    forbidden = {"terms": {"category": "FORBIDDEN", "reasons": ["forbidden band"]}}
    steer = {"floor": ALLOW, "reasons": [], "matched": [], "status": "active"}

    assert decide(steer, **forbidden) == BLOCK


def test_an_allow_floor_leaves_a_normal_decision_alone():
    steer = {"floor": ALLOW, "reasons": [], "matched": [], "status": "active"}

    assert decide(steer) == ALLOW


def test_a_confirm_floor_raises_an_allow():
    steer = {"floor": REQUIRE_CONFIRMATION, "reasons": ["rule fired"],
             "matched": ["always_confirm"], "status": "active"}

    assert decide(steer) == REQUIRE_CONFIRMATION


def test_a_block_floor_raises_an_allow():
    steer = {"floor": BLOCK, "reasons": ["rule fired"], "matched": ["never"],
             "status": "active"}

    assert decide(steer) == BLOCK


def test_an_invalid_file_forces_confirmation_on_ordinary_work():
    steer = steering_mod.evaluate(Steering(status="invalid"), action="read_table",
                                  resource="projects", role="user", blast=0.1,
                                  category="NORMAL", affected_records=1,
                                  trajectory_score=0)

    assert decide(steer) == REQUIRE_CONFIRMATION


def test_the_verdict_reports_which_rules_fired():
    steer = {"floor": BLOCK, "reasons": ["rule fired"], "matched": ["never"],
             "status": "active"}
    verdict = policy.decide(**CLEAN, steering=steer)

    assert verdict["steering"]["matched"] == ["never"]
    assert verdict["steering"]["status"] == "active"


def test_no_steering_is_reported_as_absent():
    assert policy.decide(**CLEAN)["steering"]["status"] == "absent"
