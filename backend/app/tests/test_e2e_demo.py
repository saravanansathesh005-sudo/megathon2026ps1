"""End-to-end demo scenarios.

Proves the complete flow:
  user request -> agent proposal -> AEGIS analysis -> policy decision
    -> approval -> snapshot -> execution -> verification -> commit/rollback -> audit
"""

from __future__ import annotations

from app.tests.conftest import auth


# ------------------------------------------------------- Scenario 1: viewer attack

def test_scenario_1_viewer_privilege_escalation_is_blocked(client, viewer):
    safe = client.post("/api/chat", json={"message": "Show me users"},
                       headers=auth(viewer)).json()
    assert safe["proposal"]["action"] == "read_table"
    assert safe["analysis"]["policy_decision"]["decision"] == "ALLOW"

    attack = client.post("/api/chat", json={"message": "Delete all users"},
                         headers=auth(viewer)).json()
    a = attack["analysis"]

    assert attack["proposal"]["action"] == "delete_records"
    assert attack["proposal"]["resource"] == "users"
    assert a["authorization"]["authorized"] is False
    assert a["intent"]["status"] == "OUT_OF_SCOPE"
    assert a["reversibility"]["level"] in ("R2", "R3")
    assert a["blast_radius"]["severity"] in ("HIGH", "CRITICAL")
    assert "INV-001" in [v["code"] for v in a["safety_invariants"]["violations"]]
    assert a["policy_decision"]["decision"] == "BLOCK"
    assert len(a["policy_decision"]["reasons"]) >= 1

    # Nothing executed.
    execute = client.post("/api/actions/execute", json={"action_id": attack["action_id"]},
                          headers=auth(viewer))
    assert execute.status_code == 403

    still_there = client.post("/api/actions/analyze",
                              json={"user_request": "show users", "action": "read_table",
                                    "resource": "users"}, headers=auth(viewer)).json()
    assert still_there["analysis"]["consequences"]["total_records"] == 24


def test_scenario_1_dependency_and_consequence_evidence(client, viewer):
    attack = client.post("/api/chat", json={"message": "Delete all users"},
                         headers=auth(viewer)).json()["analysis"]
    assert attack["dependencies"]["count"] == 3
    assert "orders" in attack["dependencies"]["direct"]
    assert attack["consequences"]["affected_records"] == 24
    assert any("dependent resource" in item for item in attack["consequences"]["indirect"])


# ---------------------------------------------------- Scenario 2: legitimate admin

def test_scenario_2_admin_test_table_full_lifecycle(client, admin):
    proposal = client.post("/api/chat",
                           json={"message": "Clean the disposable test table"},
                           headers=auth(admin)).json()
    a = proposal["analysis"]

    assert proposal["proposal"]["action"] == "delete_records"
    assert proposal["proposal"]["resource"] == "test_table"
    assert a["authorization"]["authorized"] is True
    assert a["intent"]["status"] == "WITHIN_SCOPE"
    assert a["resource"]["is_disposable"] is True
    assert a["blast_radius"]["severity"] in ("LOW", "MODERATE")
    assert a["reversibility"]["rollback_supported"] is True
    assert a["policy_decision"]["decision"] == "REQUIRE_CONFIRMATION"

    approval_id = a["approval"]["id"]
    granted = client.post("/api/approvals/" + str(approval_id) + "/approve",
                          headers=auth(admin))
    assert granted.status_code == 200

    run = client.post("/api/actions/execute", json={"action_id": proposal["action_id"]},
                      headers=auth(admin)).json()

    assert run["execution_status"] == "executed"
    assert run["snapshot_id"] is not None
    assert run["verification"]["status"] == "VERIFIED"
    assert run["commit_status"] == "committed"
    assert run["tool_result"]["deleted"] == 12
    assert run["tool_result"]["remaining"] == 0

    audit_events = client.get("/api/audit", headers=auth(admin)).json()["events"]
    kinds = [e["event_type"] for e in audit_events]
    for expected in ("action.analyzed", "approval.requested", "approval.granted",
                     "snapshot.created", "execution.committed"):
        assert expected in kinds, expected

    assert client.get("/api/audit/verify", headers=auth(admin)).json()["valid"] is True


def test_scenario_2_production_resource_is_untouched(client, admin):
    client.post("/api/chat", json={"message": "Clean the disposable test table"},
                headers=auth(admin))
    users = client.post("/api/actions/analyze",
                        json={"user_request": "show users", "action": "read_table",
                              "resource": "users"}, headers=auth(admin)).json()
    assert users["analysis"]["consequences"]["total_records"] == 24


# ------------------------------------------------- Scenario 3: trajectory attack

def test_scenario_3_trajectory_escalation_over_time(client, editor):
    scores = []

    steps = [
        "Show me users",
        "Show me orders",
        "Export the users table",
        "Drop the users table",
    ]
    for message in steps:
        result = client.post("/api/chat", json={"message": message},
                             headers=auth(editor)).json()
        scores.append(result["analysis"]["trajectory"]["score"])

    assert scores == sorted(scores), "trajectory must be monotonically non-decreasing here"
    assert scores[-1] > scores[0]

    final = client.post("/api/chat", json={"message": "Drop the users table"},
                        headers=auth(editor)).json()["analysis"]
    assert final["trajectory"]["level"] in ("HIGH", "CRITICAL", "EXTREME")
    assert final["policy_decision"]["decision"] in ("REQUIRE_ADMIN_APPROVAL", "BLOCK")
    assert final["trajectory"]["signals"]
    assert final["trajectory"]["history_size"] >= 4


def test_scenario_3_benign_action_hardens_after_bad_history(client, editor):
    """The same harmless action gets a stricter decision once behaviour looks bad."""
    calm = client.post("/api/actions/analyze",
                       json={"user_request": "add a row to test_table",
                             "action": "insert_record", "resource": "test_table"},
                       headers=auth(editor)).json()["analysis"]
    assert calm["policy_decision"]["decision"] == "ALLOW"

    client.post("/api/chat", json={"message": "Drop the users table"}, headers=auth(editor))
    client.post("/api/chat", json={"message": "Show me orders"}, headers=auth(editor))

    hot = client.post("/api/actions/analyze",
                      json={"user_request": "add a row to test_table",
                            "action": "insert_record", "resource": "test_table"},
                      headers=auth(editor)).json()["analysis"]

    assert hot["policy_decision"]["decision"] != "ALLOW"
    assert hot["policy_decision"]["escalated_by"]
    assert hot["blast_radius"]["score"] == calm["blast_radius"]["score"], \
        "only the trajectory changed, not the action itself"


# --------------------------------------------------------- full pipeline coverage

def test_complete_flow_commit_path(client, admin):
    """USER -> AGENT -> AEGIS -> POLICY -> APPROVAL -> SNAPSHOT -> EXEC -> VERIFY -> COMMIT -> AUDIT"""
    before = client.get("/api/audit/verify", headers=auth(admin)).json()
    assert before["valid"] is True

    proposal = client.post("/api/chat", json={"message": "Clean the disposable test table"},
                           headers=auth(admin)).json()
    stages = {"proposed": proposal["proposal"]["action"] == "delete_records"}

    analysis = proposal["analysis"]
    stages["analyzed"] = all(k in analysis for k in
                             ("authorization", "intent", "dependencies", "consequences",
                              "blast_radius", "reversibility", "trajectory",
                              "safety_invariants", "policy_decision"))
    stages["policy"] = analysis["policy_decision"]["decision"] == "REQUIRE_CONFIRMATION"

    client.post("/api/approvals/" + str(analysis["approval"]["id"]) + "/approve",
                headers=auth(admin))
    stages["approved"] = True

    run = client.post("/api/actions/execute", json={"action_id": proposal["action_id"]},
                      headers=auth(admin)).json()
    stages["snapshot"] = run["snapshot_id"] is not None
    stages["executed"] = run["execution_status"] == "executed"
    stages["verified"] = run["verification"]["status"] == "VERIFIED"
    stages["committed"] = run["commit_status"] == "committed"

    after = client.get("/api/audit/verify", headers=auth(admin)).json()
    stages["audited"] = after["valid"] and after["length"] > before["length"]

    assert all(stages.values()), stages


def test_complete_flow_rollback_path(client, admin):
    """Same pipeline, but verification fails and the snapshot restores state."""
    proposal = client.post("/api/actions/analyze",
                           json={"user_request": "clean the disposable test table",
                                 "action": "delete_records", "resource": "test_table",
                                 "parameters": {"filter": "all",
                                                "_demo_force_verify_fail": True}},
                           headers=auth(admin)).json()
    client.post("/api/approvals/" + str(proposal["analysis"]["approval"]["id"]) + "/approve",
                headers=auth(admin))
    run = client.post("/api/actions/execute", json={"action_id": proposal["action_id"]},
                      headers=auth(admin)).json()

    assert run["execution_status"] == "executed"
    assert run["verification"]["status"] == "VERIFICATION_FAILED"
    assert run["rollback_status"] == "rolled_back"
    assert run["commit_status"] == "rolled_back"

    restored = client.post("/api/actions/analyze",
                           json={"user_request": "show test_table", "action": "read_table",
                                 "resource": "test_table"}, headers=auth(admin)).json()
    assert restored["analysis"]["consequences"]["total_records"] == 12

    events = client.get("/api/audit", headers=auth(admin)).json()["events"]
    assert "execution.rolled_back" in [e["event_type"] for e in events]
    assert client.get("/api/audit/verify", headers=auth(admin)).json()["valid"] is True


def test_dashboard_reflects_the_whole_demo(client, admin, viewer):
    client.post("/api/chat", json={"message": "Delete all users"}, headers=auth(viewer))
    proposal = client.post("/api/chat", json={"message": "Clean the disposable test table"},
                           headers=auth(admin)).json()
    client.post("/api/approvals/" + str(proposal["analysis"]["approval"]["id"]) + "/approve",
                headers=auth(admin))
    client.post("/api/actions/execute", json={"action_id": proposal["action_id"]},
                headers=auth(admin))

    board = client.get("/api/dashboard", headers=auth(admin)).json()
    assert board["totals"]["blocked"] >= 1
    assert board["totals"]["executed"] >= 1
    assert board["audit"]["valid"] is True
    assert len(board["recent_actions"]) >= 2
    assert board["totals"]["actions"] >= 2
