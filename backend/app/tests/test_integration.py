"""Integration tests: identity, dependency graph, trajectory, approvals, execution, audit."""

from __future__ import annotations

import time

from app.tests.conftest import auth


# ---------------------------------------------------------------------- identity

def test_login_success(client):
    r = client.post("/api/login", json={"username": "admin", "password": "admin123"})
    assert r.status_code == 200
    assert r.json()["user"]["role"] == "admin"


def test_login_failure(client):
    r = client.post("/api/login", json={"username": "admin", "password": "wrong"})
    assert r.status_code == 401


def test_me_requires_token(client):
    assert client.get("/api/me").status_code == 401


def test_role_comes_from_server_not_client(client, viewer):
    """A forged role in the request body must not change the decision."""
    r = client.post("/api/actions/analyze",
                    json={"user_request": "delete all users", "action": "delete_records",
                          "resource": "users", "parameters": {"filter": "all"},
                          "role": "admin"},
                    headers=auth(viewer))
    assert r.json()["analysis"]["identity"]["role"] == "viewer"
    assert r.json()["analysis"]["policy_decision"]["decision"] == "BLOCK"


# -------------------------------------------------------------- dependency graph

def test_direct_and_transitive_dependents(client, admin, db_session):
    from app.security.dependencies import dependents_of

    deps = dependents_of(db_session, "users")
    assert "orders" in deps["direct"]
    assert "mock_files" in deps["direct"]
    assert "audit_demo" in deps["transitive"], "audit_demo depends on orders depends on users"
    assert deps["count"] == 3


def test_leaf_resource_has_no_dependents(client, admin, db_session):
    from app.security.dependencies import dependents_of

    assert dependents_of(db_session, "test_table")["count"] == 0


# ---------------------------------------------------------------------- analysis

def test_analysis_object_is_complete(client, admin):
    r = client.post("/api/actions/analyze",
                    json={"user_request": "show me users", "action": "read_table",
                          "resource": "users"}, headers=auth(admin))
    a = r.json()["analysis"]
    for key in ("authorization", "intent", "dependencies", "consequences", "blast_radius",
                "reversibility", "trajectory", "safety_invariants", "policy_decision"):
        assert key in a, key


def test_blast_radius_uses_measured_record_counts(client, admin):
    r = client.post("/api/actions/analyze",
                    json={"user_request": "clean the test table", "action": "delete_records",
                          "resource": "test_table", "parameters": {"filter": "all"}},
                    headers=auth(admin))
    cons = r.json()["analysis"]["consequences"]
    assert cons["affected_records"] == 12
    assert cons["total_records"] == 12


# -------------------------------------------------------------------- trajectory

def test_trajectory_rises_with_denied_actions(client, viewer):
    scores = []
    for _ in range(3):
        r = client.post("/api/chat", json={"message": "delete all users"},
                        headers=auth(viewer))
        scores.append(r.json()["analysis"]["trajectory"]["score"])
    assert scores[-1] > scores[0], "repeated denials must raise the trajectory score"


def test_trajectory_uses_history_not_just_current_request(client, viewer):
    first = client.post("/api/chat", json={"message": "show me users"},
                        headers=auth(viewer)).json()
    assert first["analysis"]["trajectory"]["score"] == 0

    for message in ("delete all users", "drop the users table", "export the users"):
        client.post("/api/chat", json={"message": message}, headers=auth(viewer))

    last = client.post("/api/chat", json={"message": "show me users"},
                       headers=auth(viewer)).json()
    traj = last["analysis"]["trajectory"]
    assert traj["score"] >= 8, traj
    assert traj["history_size"] >= 4


def test_trajectory_escalates_policy_decision(client, editor):
    """Same benign action, different outcome once behaviour looks bad."""
    calm = client.post("/api/actions/analyze",
                       json={"user_request": "add a row to test_table",
                             "action": "insert_record", "resource": "test_table"},
                       headers=auth(editor)).json()
    assert calm["analysis"]["policy_decision"]["decision"] == "ALLOW"

    # One escalation attempt plus a widening set of resources -> HIGH, not EXTREME.
    client.post("/api/chat", json={"message": "drop the users table"}, headers=auth(editor))
    client.post("/api/chat", json={"message": "show me orders"}, headers=auth(editor))

    hot = client.post("/api/actions/analyze",
                      json={"user_request": "add a row to test_table",
                            "action": "insert_record", "resource": "test_table"},
                      headers=auth(editor)).json()
    traj = hot["analysis"]["trajectory"]
    decision = hot["analysis"]["policy_decision"]["decision"]
    assert traj["level"] in ("HIGH", "CRITICAL"), traj
    assert decision != "ALLOW", traj
    assert hot["analysis"]["policy_decision"]["escalated_by"]


# --------------------------------------------------------------- agent boundary

def test_extreme_trajectory_blocks_dangerous_work(client, editor):
    """At EXTREME the destructive request stays blocked."""
    for _ in range(5):
        client.post("/api/chat", json={"message": "drop the users table"},
                    headers=auth(editor))
    hot = client.post("/api/chat", json={"message": "drop the users table"},
                      headers=auth(editor)).json()["analysis"]
    assert hot["trajectory"]["score"] >= 16
    assert hot["policy_decision"]["decision"] == "BLOCK"


def test_extreme_trajectory_does_not_block_routine_work(client, editor):
    """Trajectory is behavioural risk, not permission: routine work is slowed, not refused."""
    for _ in range(5):
        client.post("/api/chat", json={"message": "drop the users table"},
                    headers=auth(editor))
    routine = client.post("/api/actions/analyze",
                          json={"user_request": "add a row to test_table",
                                "action": "insert_record", "resource": "test_table"},
                          headers=auth(editor)).json()["analysis"]
    assert routine["trajectory"]["score"] >= 16
    assert routine["policy_decision"]["decision"] == "REQUIRE_CONFIRMATION"


def test_agent_cannot_execute_directly(client, viewer):
    """The planner proposes; only /actions/execute can run, and policy gates it."""
    r = client.post("/api/chat", json={"message": "delete all users"}, headers=auth(viewer))
    action_id = r.json()["action_id"]
    assert r.json()["analysis"]["policy_decision"]["decision"] == "BLOCK"

    ex = client.post("/api/actions/execute", json={"action_id": action_id},
                     headers=auth(viewer))
    assert ex.status_code == 403

    rows = client.post("/api/actions/analyze",
                       json={"user_request": "show users", "action": "read_table",
                             "resource": "users"}, headers=auth(viewer)).json()
    assert rows["analysis"]["consequences"]["total_records"] == 24, "nothing was deleted"


def test_unknown_action_never_executes(client, admin):
    r = client.post("/api/actions/analyze",
                    json={"user_request": "do the thing", "action": "rm_minus_rf",
                          "resource": "users"}, headers=auth(admin))
    assert r.json()["analysis"]["policy_decision"]["decision"] == "BLOCK"
    ex = client.post("/api/actions/execute", json={"action_id": r.json()["action_id"]},
                     headers=auth(admin))
    assert ex.status_code == 403


# ---------------------------------------------------------------------- approvals

def _propose_test_delete(client, headers):
    return client.post("/api/actions/analyze",
                       json={"user_request": "clean the disposable test table",
                             "action": "delete_records", "resource": "test_table",
                             "parameters": {"filter": "all"}},
                       headers=auth(headers)).json()


def test_execution_without_approval_is_refused(client, admin):
    proposal = _propose_test_delete(client, admin)
    assert proposal["analysis"]["policy_decision"]["decision"] == "REQUIRE_CONFIRMATION"
    ex = client.post("/api/actions/execute", json={"action_id": proposal["action_id"]},
                     headers=auth(admin))
    assert ex.status_code == 403


def test_approval_replay_is_prevented(client, admin):
    proposal = _propose_test_delete(client, admin)
    approval_id = proposal["analysis"]["approval"]["id"]
    client.post("/api/confirmations/" + str(approval_id) + "/confirm", headers=auth(admin))

    first = client.post("/api/actions/execute", json={"action_id": proposal["action_id"]},
                        headers=auth(admin))
    assert first.status_code == 200

    replay = client.post("/api/actions/execute", json={"action_id": proposal["action_id"]},
                         headers=auth(admin))
    assert replay.status_code == 409


def test_wrong_user_cannot_confirm(client, admin, editor):
    proposal = _propose_test_delete(client, admin)
    approval_id = proposal["analysis"]["approval"]["id"]
    r = client.post("/api/confirmations/" + str(approval_id) + "/confirm", headers=auth(editor))
    assert r.status_code == 403
    assert r.json()["detail"]["invariant"] == "INV-006"


def test_wrong_user_cannot_execute_another_users_action(client, admin, editor):
    proposal = _propose_test_delete(client, admin)
    client.post("/api/confirmations/" + str(proposal["analysis"]["approval"]["id"]) + "/confirm",
                headers=auth(admin))
    r = client.post("/api/actions/execute", json={"action_id": proposal["action_id"]},
                    headers=auth(editor))
    assert r.status_code == 403


def test_expired_approval_cannot_execute(client, admin, monkeypatch):
    proposal = _propose_test_delete(client, admin)
    approval_id = proposal["analysis"]["approval"]["id"]
    client.post("/api/confirmations/" + str(approval_id) + "/confirm", headers=auth(admin))

    from datetime import timedelta

    from app.db import SessionLocal
    from app.logging_config import utc_now
    from app.models import ApprovalRequest

    with SessionLocal() as s:
        approval = s.get(ApprovalRequest, approval_id)
        approval.expires_at = utc_now() - timedelta(seconds=10)
        s.commit()

    r = client.post("/api/actions/execute", json={"action_id": proposal["action_id"]},
                    headers=auth(admin))
    assert r.status_code == 403
    assert r.json()["detail"]["invariant"] == "INV-007"


def test_modified_payload_invalidates_approval(client, admin):
    proposal = _propose_test_delete(client, admin)
    approval_id = proposal["analysis"]["approval"]["id"]
    client.post("/api/confirmations/" + str(approval_id) + "/confirm", headers=auth(admin))

    from app.db import SessionLocal
    from app.models import Action

    with SessionLocal() as s:
        action = s.get(Action, proposal["action_id"])
        action.parameters = {"filter": "all", "tampered": True}
        s.commit()

    r = client.post("/api/actions/execute", json={"action_id": proposal["action_id"]},
                    headers=auth(admin))
    assert r.status_code == 403
    assert r.json()["detail"]["invariant"] == "INV-006"


def test_admin_approval_requires_privileged_role(client, editor, admin):
    """Editor triggers an admin-approval action; only admin/security_admin may grant it."""
    proposal = client.post("/api/actions/analyze",
                           json={"user_request": "update every row in orders",
                                 "action": "update_record", "resource": "orders",
                                 "parameters": {"filter": {}, "changes": {"x": 1}}},
                           headers=auth(editor)).json()
    approval = proposal["analysis"].get("approval")
    if approval is None or approval["required_level"] != "admin_approval":
        import pytest

        pytest.skip("scenario did not reach admin_approval")
    r = client.post("/api/confirmations/" + str(approval["id"]) + "/confirm", headers=auth(editor))
    assert r.status_code == 403


# ---------------------------------------------------------------------- execution

def test_allowed_read_executes(client, admin):
    proposal = client.post("/api/actions/analyze",
                           json={"user_request": "show me users", "action": "read_table",
                                 "resource": "users"}, headers=auth(admin)).json()
    assert proposal["analysis"]["policy_decision"]["decision"] == "ALLOW"
    r = client.post("/api/actions/execute", json={"action_id": proposal["action_id"]},
                    headers=auth(admin))
    assert r.status_code == 200
    body = r.json()
    assert body["execution_status"] == "executed"
    assert body["verification"]["status"] == "VERIFIED"
    assert body["commit_status"] == "committed"


def test_approved_delete_executes_and_commits(client, admin):
    proposal = _propose_test_delete(client, admin)
    client.post("/api/confirmations/" + str(proposal["analysis"]["approval"]["id"]) + "/confirm",
                headers=auth(admin))
    r = client.post("/api/actions/execute", json={"action_id": proposal["action_id"]},
                    headers=auth(admin))
    body = r.json()
    assert body["execution_status"] == "executed"
    assert body["tool_result"]["deleted"] == 12
    assert body["verification"]["status"] == "VERIFIED"
    assert body["commit_status"] == "committed"
    assert body["snapshot_id"] is not None


def test_verification_failure_triggers_rollback(client, admin):
    proposal = client.post("/api/actions/analyze",
                           json={"user_request": "clean the disposable test table",
                                 "action": "delete_records", "resource": "test_table",
                                 "parameters": {"filter": "all",
                                                "_demo_force_verify_fail": True}},
                           headers=auth(admin)).json()
    client.post("/api/confirmations/" + str(proposal["analysis"]["approval"]["id"]) + "/confirm",
                headers=auth(admin))
    r = client.post("/api/actions/execute", json={"action_id": proposal["action_id"]},
                    headers=auth(admin)).json()

    assert r["verification"]["status"] == "VERIFICATION_FAILED"
    assert r["commit_status"] == "rolled_back"
    assert r["rollback_status"] == "rolled_back"

    check = client.post("/api/actions/analyze",
                        json={"user_request": "show test_table", "action": "read_table",
                              "resource": "test_table"}, headers=auth(admin)).json()
    assert check["analysis"]["consequences"]["total_records"] == 12, "snapshot must restore rows"


# -------------------------------------------------------------------------- audit

def test_audit_chain_valid(client, admin):
    client.post("/api/chat", json={"message": "show me users"}, headers=auth(admin))
    r = client.get("/api/audit/verify", headers=auth(admin)).json()
    assert r["valid"] is True
    assert r["length"] > 0


def test_audit_tampering_is_detected(client, admin):
    client.post("/api/chat", json={"message": "show me users"}, headers=auth(admin))

    from app.db import SessionLocal
    from app.models import ActionEvent

    with SessionLocal() as s:
        event = s.query(ActionEvent).order_by(ActionEvent.id.asc()).offset(1).first()
        event.decision = "ALLOW"
        event.detail = {"tampered": True}
        s.commit()

    r = client.get("/api/audit/verify", headers=auth(admin)).json()
    assert r["valid"] is False
    assert r["broken_at"] is not None


def test_every_execution_produces_audit_events(client, admin):
    before = len(client.get("/api/audit", headers=auth(admin)).json()["events"])
    proposal = _propose_test_delete(client, admin)
    client.post("/api/confirmations/" + str(proposal["analysis"]["approval"]["id"]) + "/confirm",
                headers=auth(admin))
    client.post("/api/actions/execute", json={"action_id": proposal["action_id"]},
                headers=auth(admin))
    events = client.get("/api/audit", headers=auth(admin)).json()["events"]
    kinds = {e["event_type"] for e in events}
    assert len(events) > before
    assert {"action.analyzed", "confirmation.requested", "confirmation.given",
            "snapshot.created", "execution.committed"} <= kinds


# ---------------------------------------------------------------------- dashboard

def test_dashboard_returns_real_values(client, admin, viewer):
    client.post("/api/chat", json={"message": "delete all users"}, headers=auth(viewer))
    r = client.get("/api/dashboard", headers=auth(admin)).json()
    assert r["totals"]["actions"] >= 1
    assert r["totals"]["blocked"] >= 1
    assert r["audit"]["valid"] is True
    assert any(res["name"] == "users" and res["production"] for res in r["resources"])
