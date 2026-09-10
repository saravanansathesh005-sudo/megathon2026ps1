"""AEGIS API. Every mutation flows through analyse -> policy -> approval -> executor."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.agent import planner
from app.db import get_db
from app.execution import executor
from app.logging_config import get_trace_id, utc_now, utc_now_iso
from app.models import Action, ActionEvent, ApprovalRequest, Resource, User, UserSession
from app.security import analysis
from app.security.identity import (
    Identity, authenticate, create_token, current_identity, new_session_id,
)
from app.security.policy import ALLOW, BLOCK, REQUIRE_ADMIN_APPROVAL, REQUIRE_CONFIRMATION
from app.services import approvals, audit, seed

router = APIRouter(prefix="/api")


class LoginRequest(BaseModel):
    username: str
    password: str


class ChatRequest(BaseModel):
    message: str


class AnalyzeRequest(BaseModel):
    user_request: str = ""
    action: str
    resource: str = ""
    parameters: dict = {}


class ExecuteRequest(BaseModel):
    action_id: int


class RejectRequest(BaseModel):
    reason: str = ""


# --------------------------------------------------------------------------- auth

@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate(db, payload.username, payload.password)
    if user is None:
        audit.record(db, event_type="auth.login_failed", username=payload.username,
                     detail={"reason": "invalid credentials"})
        db.commit()
        raise HTTPException(status_code=401, detail="invalid username or password")

    session = UserSession(id=new_session_id(), user_id=user.id, agent_id=planner.AGENT_ID)
    db.add(session)
    db.flush()
    token = create_token(user, session.id, planner.AGENT_ID)
    audit.record(db, event_type="auth.login", username=user.username,
                 session_id=session.id, agent_id=planner.AGENT_ID)
    db.commit()
    return {"token": token, "user": {"username": user.username, "role": user.role,
                                     "display_name": user.display_name},
            "session_id": session.id, "agent_id": planner.AGENT_ID}


@router.get("/me")
def me(identity: Identity = Depends(current_identity)):
    return {"username": identity.username, "role": identity.role,
            "session_id": identity.session_id, "agent_id": identity.agent_id,
            "user_id": identity.user_id}


# ------------------------------------------------------------------- analysis core

def _persist(db: Session, identity: Identity, result: dict, user_request: str) -> Action:
    decision = result["policy_decision"]["decision"]
    action = Action(
        created_at=utc_now(), user_id=identity.user_id, username=identity.username,
        role=identity.role, agent_id=identity.agent_id, session_id=identity.session_id,
        trace_id=get_trace_id() or "", user_request=user_request,
        action_name=result["action"]["name"], resource_name=result["action"]["resource"],
        parameters=result["action"]["parameters"], action_hash=result["action"]["hash"],
        analysis=result, decision=decision,
        blast_radius=result["blast_radius"]["score"],
        reversibility=result["reversibility"]["level"],
        trajectory_score=result["trajectory"]["score"],
        intent_status=result["intent"]["status"],
        authorized=result["authorization"]["authorized"],
    )
    db.add(action)
    db.flush()

    audit.record(db, event_type="action.analyzed", action_id=action.id,
                 username=identity.username, agent_id=identity.agent_id,
                 session_id=identity.session_id, action_name=action.action_name,
                 resource_name=action.resource_name, decision=decision,
                 detail={"blast_radius": action.blast_radius,
                         "reversibility": action.reversibility,
                         "trajectory": action.trajectory_score,
                         "intent": action.intent_status,
                         "reasons": result["policy_decision"]["reasons"]})

    if decision == BLOCK:
        action.execution_status = "blocked"
        audit.record(db, event_type="action.blocked", action_id=action.id,
                     username=identity.username, agent_id=identity.agent_id,
                     session_id=identity.session_id, action_name=action.action_name,
                     resource_name=action.resource_name, decision=BLOCK,
                     detail={"reasons": result["policy_decision"]["reasons"]})
    elif decision in (REQUIRE_CONFIRMATION, REQUIRE_ADMIN_APPROVAL):
        request = approvals.create(db, action, identity, decision)
        action.execution_status = "awaiting_approval"
        result["approval"] = {"id": request.id, "required_level": request.required_level,
                              "status": request.status,
                              "expires_at": request.expires_at.isoformat()}
        audit.record(db, event_type="approval.requested", action_id=action.id,
                     username=identity.username, agent_id=identity.agent_id,
                     session_id=identity.session_id, action_name=action.action_name,
                     resource_name=action.resource_name, decision=decision,
                     detail={"approval_id": request.id, "level": request.required_level})
    else:
        action.execution_status = "ready"

    action.analysis = dict(result)
    flag_modified(action, "analysis")  # JSON column: force the UPDATE
    db.commit()
    db.refresh(action)
    return action


@router.post("/actions/analyze")
def analyze(payload: AnalyzeRequest, db: Session = Depends(get_db),
            identity: Identity = Depends(current_identity)):
    result = analysis.analyse(db, identity, payload.user_request or payload.action,
                              payload.action, payload.resource, payload.parameters)
    action = _persist(db, identity, result, payload.user_request or payload.action)
    return {"action_id": action.id, "analysis": action.analysis}


@router.post("/chat")
def chat(payload: ChatRequest, db: Session = Depends(get_db),
         identity: Identity = Depends(current_identity)):
    """User request -> agent proposal -> AEGIS analysis. The agent cannot execute."""
    proposal = planner.plan(payload.message)
    result = analysis.analyse(db, identity, payload.message, proposal["action"],
                              proposal["resource"], proposal["parameters"])
    action = _persist(db, identity, result, payload.message)
    return {"action_id": action.id, "proposal": proposal, "analysis": action.analysis}


# ---------------------------------------------------------------------- execution

@router.post("/actions/execute")
def execute_action(payload: ExecuteRequest, db: Session = Depends(get_db),
                   identity: Identity = Depends(current_identity)):
    action = db.get(Action, payload.action_id)
    if action is None:
        raise HTTPException(status_code=404, detail="unknown action")
    if action.user_id != identity.user_id or action.session_id != identity.session_id:
        raise HTTPException(status_code=403,
                            detail="action belongs to another user or session (INV-006)")
    if action.execution_status in ("executed", "failed"):
        raise HTTPException(status_code=409,
                            detail="action already resolved: " + action.execution_status)

    approval = db.scalar(
        select(ApprovalRequest).where(ApprovalRequest.action_id == action.id)
        .order_by(ApprovalRequest.id.desc()).limit(1))
    approval_present = approval is not None and approval.status == "approved" \
        and not approval.consumed

    # RULE 6: re-run policy now. Never trust a decision made minutes ago.
    fresh = analysis.analyse(db, identity, action.user_request, action.action_name,
                             action.resource_name, action.parameters,
                             approval_present=approval_present)
    decision = fresh["policy_decision"]["decision"]
    action.analysis = fresh
    action.decision = decision

    if decision == BLOCK:
        action.execution_status = "blocked"
        audit.record(db, event_type="execution.denied", action_id=action.id,
                     username=identity.username, agent_id=identity.agent_id,
                     session_id=identity.session_id, action_name=action.action_name,
                     resource_name=action.resource_name, decision=BLOCK,
                     detail={"reasons": fresh["policy_decision"]["reasons"],
                             "stage": "re-check"})
        db.commit()
        raise HTTPException(status_code=403, detail={
            "error": "blocked by policy on re-check",
            "reasons": fresh["policy_decision"]["reasons"]})

    if decision in (REQUIRE_CONFIRMATION, REQUIRE_ADMIN_APPROVAL):
        current_hash = analysis.action_hash(action.action_name, action.resource_name,
                                            action.parameters or {})
        ok, reason, code = approvals.validate_for_execution(
            db, approval, action, identity, current_hash=current_hash)
        if not ok:
            audit.record(db, event_type="execution.denied", action_id=action.id,
                         username=identity.username, agent_id=identity.agent_id,
                         session_id=identity.session_id, action_name=action.action_name,
                         resource_name=action.resource_name, decision="BLOCK",
                         detail={"reason": reason, "invariant": code})
            db.commit()
            raise HTTPException(status_code=403,
                                detail={"error": reason, "invariant": code})
        approval.consumed = True
        db.flush()

    snapshot_required = fresh["reversibility"]["rollback_supported"] and \
        fresh["reversibility"]["level"] != "R0"
    outcome = executor.execute(db, action, snapshot_required=snapshot_required)
    db.refresh(action)
    return {"action_id": action.id, "decision": decision, **outcome,
            "analysis": action.analysis}


# ---------------------------------------------------------------------- approvals

@router.get("/approvals")
def list_approvals(db: Session = Depends(get_db),
                   identity: Identity = Depends(current_identity)):
    rows = db.scalars(select(ApprovalRequest).order_by(ApprovalRequest.id.desc())
                      .limit(50)).all()
    out = []
    for row in rows:
        action = db.get(Action, row.action_id)
        allowed, why = approvals.can_decide(row, identity)
        out.append({
            "id": row.id, "action_id": row.action_id, "status": row.status,
            "required_level": row.required_level, "consumed": row.consumed,
            "expires_at": row.expires_at.isoformat() if row.expires_at else None,
            "action_name": action.action_name if action else "",
            "resource": action.resource_name if action else "",
            "requested_by": action.username if action else "",
            "blast_radius": action.blast_radius if action else 0,
            "reversibility": action.reversibility if action else "",
            "you_may_decide": allowed, "decide_note": why,
        })
    return {"approvals": out}


@router.post("/approvals/{approval_id}/approve")
def approve(approval_id: int, db: Session = Depends(get_db),
            identity: Identity = Depends(current_identity)):
    approval = db.get(ApprovalRequest, approval_id)
    if approval is None:
        raise HTTPException(status_code=404, detail="unknown approval")
    if approval.status != "pending":
        raise HTTPException(status_code=409, detail="approval already " + approval.status)

    expires = approval.expires_at
    if expires is not None and expires.tzinfo is None:
        from datetime import timezone
        expires = expires.replace(tzinfo=timezone.utc)
    if expires is not None and expires < utc_now():
        approval.status = "expired"
        audit.record(db, event_type="approval.expired", action_id=approval.action_id,
                     username=identity.username, detail={"approval_id": approval.id,
                                                         "invariant": "INV-007"})
        db.commit()
        raise HTTPException(status_code=403,
                            detail={"error": "approval expired", "invariant": "INV-007"})

    allowed, why = approvals.can_decide(approval, identity)
    if not allowed:
        audit.record(db, event_type="approval.denied", action_id=approval.action_id,
                     username=identity.username, detail={"approval_id": approval.id,
                                                         "reason": why,
                                                         "invariant": "INV-006"})
        db.commit()
        raise HTTPException(status_code=403, detail={"error": why, "invariant": "INV-006"})

    approval.status = "approved"
    approval.approved_by_user_id = identity.user_id
    approval.decided_at = utc_now()
    audit.record(db, event_type="approval.granted", action_id=approval.action_id,
                 username=identity.username, session_id=identity.session_id,
                 decision="APPROVED", detail={"approval_id": approval.id, "note": why})
    db.commit()
    return {"id": approval.id, "status": approval.status, "approved_by": identity.username}


@router.post("/approvals/{approval_id}/reject")
def reject(approval_id: int, payload: RejectRequest, db: Session = Depends(get_db),
           identity: Identity = Depends(current_identity)):
    approval = db.get(ApprovalRequest, approval_id)
    if approval is None:
        raise HTTPException(status_code=404, detail="unknown approval")
    allowed, why = approvals.can_decide(approval, identity)
    if not allowed:
        raise HTTPException(status_code=403, detail={"error": why, "invariant": "INV-006"})
    approval.status = "rejected"
    approval.reason = payload.reason
    approval.decided_at = utc_now()
    action = db.get(Action, approval.action_id)
    if action:
        action.execution_status = "rejected"
    audit.record(db, event_type="approval.rejected", action_id=approval.action_id,
                 username=identity.username, decision="REJECTED",
                 detail={"approval_id": approval.id, "reason": payload.reason})
    db.commit()
    return {"id": approval.id, "status": approval.status}


# ------------------------------------------------------------------------ reading

def _action_summary(a: Action) -> dict:
    return {"id": a.id, "created_at": a.created_at.isoformat() if a.created_at else None,
            "user": a.username, "role": a.role, "agent": a.agent_id,
            "session": a.session_id, "user_request": a.user_request,
            "action": a.action_name, "resource": a.resource_name,
            "decision": a.decision, "blast_radius": a.blast_radius,
            "reversibility": a.reversibility, "trajectory": a.trajectory_score,
            "intent": a.intent_status, "authorized": a.authorized,
            "execution_status": a.execution_status,
            "verification_status": a.verification_status,
            "commit_status": a.commit_status}


@router.get("/actions")
def list_actions(limit: int = 50, db: Session = Depends(get_db),
                 identity: Identity = Depends(current_identity)):
    rows = db.scalars(select(Action).order_by(Action.id.desc()).limit(limit)).all()
    return {"actions": [_action_summary(a) for a in rows]}


@router.get("/actions/{action_id}")
def get_action(action_id: int, db: Session = Depends(get_db),
               identity: Identity = Depends(current_identity)):
    action = db.get(Action, action_id)
    if action is None:
        raise HTTPException(status_code=404, detail="unknown action")
    return {**_action_summary(action), "analysis": action.analysis, "result": action.result}


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db),
              identity: Identity = Depends(current_identity)):
    total = db.scalar(select(func.count(Action.id))) or 0
    blocked = db.scalar(select(func.count(Action.id)).where(Action.decision == BLOCK)) or 0
    pending = db.scalar(select(func.count(ApprovalRequest.id))
                        .where(ApprovalRequest.status == "pending")) or 0
    executed = db.scalar(select(func.count(Action.id))
                         .where(Action.execution_status == "executed")) or 0
    rolled_back = db.scalar(select(func.count(Action.id))
                            .where(Action.commit_status == "rolled_back")) or 0
    high_risk = db.scalar(select(func.count(Action.id))
                          .where(Action.blast_radius >= 5.0)) or 0
    recent = db.scalars(select(Action).order_by(Action.id.desc()).limit(10)).all()
    my_last = db.scalar(select(Action).where(Action.user_id == identity.user_id)
                        .order_by(Action.id.desc()).limit(1))
    resources = db.scalars(select(Resource)).all()
    return {
        "generated_at": utc_now_iso(),
        "totals": {"actions": total, "blocked": blocked, "pending_approvals": pending,
                   "executed": executed, "rolled_back": rolled_back,
                   "high_risk": high_risk},
        "trajectory": {"score": my_last.trajectory_score if my_last else 0,
                       "user": identity.username},
        "audit": audit.verify_chain(db),
        "recent_actions": [_action_summary(a) for a in recent],
        "resources": [{"name": r.name, "production": r.is_production,
                       "sensitive": r.is_sensitive, "criticality": r.criticality,
                       "disposable": r.is_disposable, "dropped": r.dropped}
                      for r in resources],
    }


@router.get("/audit")
def get_audit(limit: int = 100, db: Session = Depends(get_db),
              identity: Identity = Depends(current_identity)):
    rows = db.scalars(select(ActionEvent).order_by(ActionEvent.id.desc()).limit(limit)).all()
    return {"events": [{
        "id": e.id, "timestamp": e.timestamp.isoformat() if e.timestamp else None,
        "action_id": e.action_id, "event_type": e.event_type, "user": e.username,
        "agent": e.agent_id, "session": e.session_id, "action": e.action_name,
        "resource": e.resource_name, "decision": e.decision, "detail": e.detail,
        "previous_hash": e.previous_hash, "current_hash": e.current_hash,
    } for e in rows]}


@router.get("/audit/verify")
def verify_audit(db: Session = Depends(get_db),
                 identity: Identity = Depends(current_identity)):
    return audit.verify_chain(db)


@router.post("/demo/reset")
def demo_reset(db: Session = Depends(get_db)):
    stats = seed.reset(db)
    audit.record(db, event_type="demo.reset", detail=stats)
    db.commit()
    return {"reset": True, **stats}
