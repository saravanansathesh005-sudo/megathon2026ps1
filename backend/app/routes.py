"""AEGIS API.

Every mutation flows through analyse -> policy -> (confirmation) -> executor.
AEGIS decides automatically: ALLOW, REQUIRE_CONFIRMATION or BLOCK. There is no
administrator approval workflow and no manual override anywhere in this file.
"""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.agent import gemini, planner
from app.config import get_settings
from app.db import get_db
from app.execution import executor
from app.logging_config import get_trace_id, utc_now, utc_now_iso
from app.models import (
    Action, ActionEvent, ApprovalRequest, Conversation, Message, Resource,
    SecurityRestriction, User, UserSession,
)
from app.security import analysis, google_auth
from app.security.identity import (
    Identity, authenticate, create_token, current_identity, new_session_id,
    require_observer, upsert_google_user,
)
from app.security.policy import ALLOW, BLOCK, REQUIRE_CONFIRMATION
from app.security.registry import ACTIONS, OBSERVER_ROLES
from app.services import approvals, audit, seed

router = APIRouter(prefix="/api")
settings = get_settings()

# In-memory CSRF state for the OAuth round trip.
_oauth_states: set[str] = set()

RESTRICTION_TRAJECTORY = 12
RESTRICTION_MINUTES = 15


class LoginRequest(BaseModel):
    username: str
    password: str


class ChatRequest(BaseModel):
    message: str
    conversation_id: int | None = None


class AnalyzeRequest(BaseModel):
    user_request: str = ""
    action: str
    resource: str = ""
    parameters: dict = {}


class ExecuteRequest(BaseModel):
    action_id: int
    confirmation_id: int | None = None


# =============================================================== authentication

@router.get("/auth/config")
def auth_config():
    """What sign-in methods this deployment offers. No secrets."""
    return {
        "google": google_auth.configured(),
        "password": settings.ALLOW_PASSWORD_LOGIN
        and settings.ENVIRONMENT != "production",
        "gemini": gemini.available(),
    }


@router.get("/auth/google/start")
def google_start():
    if not google_auth.configured():
        raise HTTPException(status_code=503,
                            detail="Google sign-in is not configured on this server")
    state = google_auth.new_state()
    _oauth_states.add(state)
    return {"authorization_url": google_auth.authorization_url(state)}


@router.get("/auth/google/callback")
def google_callback(code: str = Query(""), state: str = Query(""),
                    db: Session = Depends(get_db)):
    if state not in _oauth_states:
        raise HTTPException(status_code=400, detail="invalid or expired OAuth state")
    _oauth_states.discard(state)
    try:
        claims = google_auth.exchange(code)
    except google_auth.GoogleAuthError as exc:
        audit.record(db, event_type="auth.google_failed", detail={"reason": str(exc)})
        db.commit()
        raise HTTPException(status_code=401, detail=str(exc))

    user = upsert_google_user(db, claims)
    session = UserSession(id=new_session_id(), user_id=user.id, agent_id=planner.AGENT_ID)
    db.add(session)
    db.flush()
    token = create_token(user, session.id, planner.AGENT_ID)
    audit.record(db, event_type="auth.login", username=user.username,
                 session_id=session.id, agent_id=planner.AGENT_ID,
                 detail={"method": "google"})
    db.commit()
    return RedirectResponse(settings.FRONTEND_ORIGIN + "/auth/callback#token=" + token)


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Password login for the seeded demo accounts. Refused in production."""
    if not settings.ALLOW_PASSWORD_LOGIN or settings.ENVIRONMENT == "production":
        raise HTTPException(status_code=403,
                            detail="password login is disabled; use Google sign-in")
    user = authenticate(db, payload.username, payload.password)
    if user is None:
        audit.record(db, event_type="auth.login_failed", username=payload.username,
                     detail={"reason": "invalid credentials"})
        db.commit()
        raise HTTPException(status_code=401, detail="invalid username or password")

    user.last_login = utc_now()
    session = UserSession(id=new_session_id(), user_id=user.id, agent_id=planner.AGENT_ID)
    db.add(session)
    db.flush()
    token = create_token(user, session.id, planner.AGENT_ID)
    audit.record(db, event_type="auth.login", username=user.username,
                 session_id=session.id, agent_id=planner.AGENT_ID,
                 detail={"method": "password"})
    db.commit()
    return {"token": token, "user": {"username": user.username, "role": user.role,
                                     "display_name": user.display_name,
                                     "email": user.email},
            "session_id": session.id, "agent_id": planner.AGENT_ID}


@router.get("/me")
def me(identity: Identity = Depends(current_identity), db: Session = Depends(get_db)):
    user = db.get(User, identity.user_id)
    return {"username": identity.username, "role": identity.role,
            "session_id": identity.session_id, "agent_id": identity.agent_id,
            "user_id": identity.user_id,
            "display_name": user.display_name if user else identity.username,
            "email": user.email if user else None,
            "is_observer": identity.role in OBSERVER_ROLES}


@router.post("/logout")
def logout(identity: Identity = Depends(current_identity), db: Session = Depends(get_db)):
    """Ends the session. Security history is deliberately NOT erased."""
    session = db.get(UserSession, identity.session_id)
    if session:
        session.active = False
    audit.record(db, event_type="auth.logout", username=identity.username,
                 session_id=identity.session_id)
    db.commit()
    return {"ok": True, "security_history_retained": True}


# ================================================================ analysis core

def _restriction_for(db: Session, user_id: int) -> SecurityRestriction | None:
    row = db.scalar(select(SecurityRestriction)
                    .where(SecurityRestriction.user_id == user_id)
                    .order_by(SecurityRestriction.id.desc()).limit(1))
    if row is None:
        return None
    expires = row.expires_at
    if expires is not None and expires.tzinfo is None:
        from datetime import timezone
        expires = expires.replace(tzinfo=timezone.utc)
    return row if expires and expires > utc_now() else None


def _apply_automatic_restriction(db: Session, identity: Identity, result: dict) -> None:
    """AEGIS restricts sustained bad behaviour itself. Temporary, no human unblock."""
    traj = result["trajectory"]
    if traj["score"] < RESTRICTION_TRAJECTORY:
        return
    if _restriction_for(db, identity.user_id) is not None:
        return
    db.add(SecurityRestriction(
        user_id=identity.user_id,
        reason="trajectory " + str(traj["score"]) + "/20 (" + traj["level"] + "): "
               + "; ".join(traj["signals"][:3]),
        trajectory_score=traj["score"],
        created_at=utc_now(),
        expires_at=utc_now() + timedelta(minutes=RESTRICTION_MINUTES),
    ))
    audit.record(db, event_type="security.restriction_applied",
                 username=identity.username, session_id=identity.session_id,
                 detail={"trajectory": traj["score"], "level": traj["level"],
                         "expires_in_minutes": RESTRICTION_MINUTES})


def _persist(db: Session, identity: Identity, result: dict, user_request: str,
             conversation_id: int | None = None,
             proposal_source: str = "demo-planner") -> Action:
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
        terms_category=result["terms"]["category"],
        conversation_id=conversation_id,
        proposal_source=proposal_source,
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
                         "terms": action.terms_category,
                         "intent": action.intent_status,
                         "reasons": result["policy_decision"]["reasons"]})

    if result["injection"]["detected"]:
        audit.record(db, event_type="security.injection_attempt", action_id=action.id,
                     username=identity.username, session_id=identity.session_id,
                     detail={"signals": result["injection"]["signals"]})

    if decision == BLOCK:
        action.execution_status = "blocked"
        audit.record(db, event_type="action.blocked", action_id=action.id,
                     username=identity.username, agent_id=identity.agent_id,
                     session_id=identity.session_id, action_name=action.action_name,
                     resource_name=action.resource_name, decision=BLOCK,
                     detail={"reasons": result["policy_decision"]["reasons"]})
    elif decision == REQUIRE_CONFIRMATION:
        request = approvals.create(db, action, identity, decision)
        action.execution_status = "awaiting_confirmation"
        result["confirmation"] = {"id": request.id, "status": request.status,
                                  "expires_at": request.expires_at.isoformat()}
        # Legacy key retained so existing clients/tests keep working.
        result["approval"] = dict(result["confirmation"], required_level="confirmation")
        audit.record(db, event_type="confirmation.requested", action_id=action.id,
                     username=identity.username, agent_id=identity.agent_id,
                     session_id=identity.session_id, action_name=action.action_name,
                     resource_name=action.resource_name, decision=decision,
                     detail={"confirmation_id": request.id})
    else:
        action.execution_status = "ready"

    _apply_automatic_restriction(db, identity, result)

    action.analysis = dict(result)
    flag_modified(action, "analysis")
    db.commit()
    db.refresh(action)
    return action


@router.post("/actions/analyze")
def analyze(payload: AnalyzeRequest, db: Session = Depends(get_db),
            identity: Identity = Depends(current_identity)):
    result = analysis.analyse(db, identity, payload.user_request or payload.action,
                              payload.action, payload.resource, payload.parameters)
    action = _persist(db, identity, result, payload.user_request or payload.action,
                      proposal_source="direct")
    return {"action_id": action.id, "analysis": action.analysis}


# ========================================================== conversations / chat

def _own_conversation(db: Session, identity: Identity, conversation_id: int) -> Conversation:
    convo = db.get(Conversation, conversation_id)
    if convo is None or convo.user_id != identity.user_id:
        # Same response whether it does not exist or belongs to someone else.
        raise HTTPException(status_code=404, detail="conversation not found")
    return convo


@router.get("/conversations")
def list_conversations(db: Session = Depends(get_db),
                       identity: Identity = Depends(current_identity)):
    rows = db.scalars(select(Conversation)
                      .where(Conversation.user_id == identity.user_id)
                      .order_by(Conversation.updated_at.desc()).limit(50)).all()
    return {"conversations": [{"id": c.id, "title": c.title,
                               "updated_at": c.updated_at.isoformat() if c.updated_at else None}
                              for c in rows]}


@router.post("/conversations")
def create_conversation(db: Session = Depends(get_db),
                        identity: Identity = Depends(current_identity)):
    convo = Conversation(user_id=identity.user_id, title="New chat",
                         created_at=utc_now(), updated_at=utc_now())
    db.add(convo)
    db.commit()
    return {"id": convo.id, "title": convo.title}


@router.get("/conversations/{conversation_id}/messages")
def list_messages(conversation_id: int, db: Session = Depends(get_db),
                  identity: Identity = Depends(current_identity)):
    _own_conversation(db, identity, conversation_id)
    rows = db.scalars(select(Message)
                      .where(Message.conversation_id == conversation_id)
                      .order_by(Message.id.asc())).all()
    return {"messages": [{"id": m.id, "role": m.role, "content": m.content,
                          "kind": m.kind, "action_id": m.action_id,
                          "created_at": m.created_at.isoformat() if m.created_at else None}
                         for m in rows]}


def _assistant_text(decision: str, action_name: str, result: dict) -> str:
    spec = ACTIONS.get(action_name)
    label = spec.description.lower() if spec else action_name
    if decision == ALLOW:
        return "Sure — I'll " + label + "."
    if decision == REQUIRE_CONFIRMATION:
        return "That will " + label + ". I need you to confirm before I do it."
    return "I can't do that."


# Invariant -> what a normal user should be told. Ordered by how the policy engine
# actually decides, so the sentence shown always names the check that fired.
_INVARIANT_REASON = {
    "INV-002": "That is not an action I can perform.",
    "INV-003": "This would make a destructive change to a production resource, "
               "which your account may not do.",
    "INV-001": "You are not authorized to perform this action.",
}


def _friendly_block_reason(result: dict) -> str:
    """Short, non-sensitive explanation naming the check that actually failed."""
    resource = result.get("resource", {})
    if resource.get("name") and not resource.get("exists", True):
        return "There is no resource named '" + str(resource["name"]) + "'."

    # "Never permitted" outranks "you specifically may not": it is the truer sentence.
    if result["terms"]["category"] == "FORBIDDEN":
        if result["injection"]["detected"]:
            return ("That request asks me to work around the security policy, so I "
                    "stopped. AEGIS decided this automatically.")
        return "This operation is never permitted, for any account."

    violated = [v["code"] for v in result["safety_invariants"]["violations"]
                if v["code"] != "INV-004"]
    for code in ("INV-002", "INV-003", "INV-001"):
        if code in violated:
            return _INVARIANT_REASON[code]

    if not result["authorization"]["authorized"]:
        return "You are not authorized to perform this action."
    if result["intent"]["status"] == "OUT_OF_SCOPE":
        return "That goes beyond what you asked for, so I stopped."
    if result["trajectory"]["score"] >= RESTRICTION_TRAJECTORY:
        return "Repeated suspicious activity has caused AEGIS to restrict this operation."
    blast = result.get("blast_radius", {})
    if blast.get("score", 0) >= 7.5:
        return ("This would affect too much at once (impact "
                + str(blast["score"]) + "/10) to run.")
    return "This operation is too dangerous to execute."


@router.post("/chat")
def chat(payload: ChatRequest, db: Session = Depends(get_db),
         identity: Identity = Depends(current_identity)):
    """User request -> planner proposal -> AEGIS analysis. The agent cannot execute."""
    if payload.conversation_id is not None:
        convo = _own_conversation(db, identity, payload.conversation_id)
    else:
        convo = Conversation(user_id=identity.user_id, created_at=utc_now(),
                             updated_at=utc_now(),
                             title=(payload.message or "New chat")[:60])
        db.add(convo)
        db.flush()

    db.add(Message(conversation_id=convo.id, user_id=identity.user_id,
                   role="user", content=payload.message, created_at=utc_now()))
    convo.updated_at = utc_now()
    db.flush()

    proposal = gemini.propose(payload.message)
    source = proposal.get("source", "demo-planner")

    # Conversation, not work. No action is proposed, so there is nothing to
    # authorise and nothing to execute. Recorded, but not as a security decision.
    if proposal.get("action") == "none":
        reply = proposal.get("reply") or planner.CONVERSATIONAL_REPLY
        db.add(Message(conversation_id=convo.id, user_id=identity.user_id,
                       role="assistant", content=reply, kind="text",
                       created_at=utc_now()))
        audit.record(db, event_type="chat.conversational",
                     username=identity.username, agent_id=identity.agent_id,
                     session_id=identity.session_id,
                     detail={"source": source})
        db.commit()
        return {"conversation_id": convo.id, "action_id": None, "decision": None,
                "message": reply, "kind": "text",
                "proposal": {"action": "none", "resource": "", "parameters": {},
                             "reasoning_summary": proposal.get("reasoning_summary", ""),
                             "source": source, "error": proposal.get("error")},
                "confirmation": None, "block_reason": None, "analysis": None}

    result = analysis.analyse(db, identity, payload.message, proposal["action"],
                              proposal.get("resource", ""), proposal.get("parameters", {}))
    result["proposal"] = {"action": proposal["action"],
                          "resource": proposal.get("resource", ""),
                          "parameters": proposal.get("parameters", {}),
                          "reasoning_summary": proposal.get("reasoning_summary", ""),
                          "source": source,
                          "error": proposal.get("error")}
    action = _persist(db, identity, result, payload.message,
                      conversation_id=convo.id, proposal_source=source)

    decision = action.analysis["policy_decision"]["decision"]
    kind = {ALLOW: "text", REQUIRE_CONFIRMATION: "confirm", BLOCK: "blocked"}[decision]
    text = (_assistant_text(decision, proposal["action"], action.analysis)
            if decision != BLOCK
            else "Action blocked. " + _friendly_block_reason(action.analysis))
    db.add(Message(conversation_id=convo.id, user_id=identity.user_id,
                   role="assistant", content=text, kind=kind,
                   action_id=action.id, created_at=utc_now()))
    db.commit()

    return {
        "conversation_id": convo.id,
        "action_id": action.id,
        "decision": decision,
        "message": text,
        "kind": kind,
        "proposal": result["proposal"],
        "confirmation": action.analysis.get("confirmation"),
        "block_reason": _friendly_block_reason(action.analysis) if decision == BLOCK else None,
        "analysis": action.analysis,
    }


# =================================================================== execution

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

    confirmation = db.scalar(
        select(ApprovalRequest).where(ApprovalRequest.action_id == action.id)
        .order_by(ApprovalRequest.id.desc()).limit(1))
    confirmed = (confirmation is not None and confirmation.status == "approved"
                 and not confirmation.consumed)

    # Policy is re-run from scratch. A decision made minutes ago is never trusted,
    # and a `confirmed` flag from any client can never by itself authorise execution.
    fresh = analysis.analyse(db, identity, action.user_request, action.action_name,
                             action.resource_name, action.parameters,
                             approval_present=confirmed)
    decision = fresh["policy_decision"]["decision"]
    action.analysis = fresh
    flag_modified(action, "analysis")
    action.decision = decision
    action.terms_category = fresh["terms"]["category"]

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
            "reason": _friendly_block_reason(fresh),
            "reasons": fresh["policy_decision"]["reasons"]})

    if decision == REQUIRE_CONFIRMATION:
        current_hash = analysis.action_hash(action.action_name, action.resource_name,
                                            action.parameters or {})
        ok, reason, code = approvals.validate_for_execution(
            db, confirmation, action, identity, current_hash=current_hash)
        if not ok:
            audit.record(db, event_type="execution.denied", action_id=action.id,
                         username=identity.username, agent_id=identity.agent_id,
                         session_id=identity.session_id, action_name=action.action_name,
                         resource_name=action.resource_name, decision="BLOCK",
                         detail={"reason": reason, "invariant": code})
            db.commit()
            raise HTTPException(status_code=403,
                                detail={"error": reason, "invariant": code})
        confirmation.consumed = True
        db.flush()

    # Ownership is injected by the backend, never taken from the proposal.
    params = dict(action.parameters or {})
    params["_owner_user_id"] = identity.user_id
    action.parameters = params
    flag_modified(action, "parameters")

    snapshot_required = fresh["reversibility"]["rollback_supported"] and \
        fresh["reversibility"]["level"] != "R0"
    outcome = executor.execute(db, action, snapshot_required=snapshot_required)
    db.refresh(action)

    if action.conversation_id:
        summary = "Done." if outcome["execution_status"] == "executed" else "That didn't complete."
        if outcome.get("commit_status") == "rolled_back":
            summary = "Verification failed, so I rolled the change back. Nothing was left changed."
        db.add(Message(conversation_id=action.conversation_id, user_id=identity.user_id,
                       role="assistant", content=summary, kind="result",
                       action_id=action.id, created_at=utc_now()))
        db.commit()

    return {"action_id": action.id, "decision": decision, **outcome,
            "analysis": action.analysis}


# ================================================================ confirmations

@router.post("/confirmations/{confirmation_id}/confirm")
def confirm(confirmation_id: int, db: Session = Depends(get_db),
            identity: Identity = Depends(current_identity)):
    """The requesting user confirms their own risky action. Not an approval workflow."""
    record = db.get(ApprovalRequest, confirmation_id)
    if record is None:
        raise HTTPException(status_code=404, detail="unknown confirmation")
    if record.status != "pending":
        raise HTTPException(status_code=409, detail="confirmation already " + record.status)

    expires = record.expires_at
    if expires is not None and expires.tzinfo is None:
        from datetime import timezone
        expires = expires.replace(tzinfo=timezone.utc)
    if expires is not None and expires < utc_now():
        record.status = "expired"
        audit.record(db, event_type="confirmation.expired", action_id=record.action_id,
                     username=identity.username,
                     detail={"confirmation_id": record.id, "invariant": "INV-007"})
        db.commit()
        raise HTTPException(status_code=403,
                            detail={"error": "confirmation expired", "invariant": "INV-007"})

    allowed, why = approvals.can_decide(record, identity)
    if not allowed:
        audit.record(db, event_type="confirmation.denied", action_id=record.action_id,
                     username=identity.username,
                     detail={"confirmation_id": record.id, "reason": why,
                             "invariant": "INV-006"})
        db.commit()
        raise HTTPException(status_code=403, detail={"error": why, "invariant": "INV-006"})

    record.status = "approved"
    record.approved_by_user_id = identity.user_id
    record.decided_at = utc_now()
    audit.record(db, event_type="confirmation.given", action_id=record.action_id,
                 username=identity.username, session_id=identity.session_id,
                 decision="CONFIRMED", detail={"confirmation_id": record.id})
    db.commit()
    return {"id": record.id, "status": record.status, "confirmed_by": identity.username}


@router.post("/confirmations/{confirmation_id}/cancel")
def cancel(confirmation_id: int, db: Session = Depends(get_db),
           identity: Identity = Depends(current_identity)):
    record = db.get(ApprovalRequest, confirmation_id)
    if record is None:
        raise HTTPException(status_code=404, detail="unknown confirmation")
    allowed, why = approvals.can_decide(record, identity)
    if not allowed:
        raise HTTPException(status_code=403, detail={"error": why, "invariant": "INV-006"})
    record.status = "cancelled"
    record.decided_at = utc_now()
    action = db.get(Action, record.action_id)
    if action:
        action.execution_status = "cancelled"
    audit.record(db, event_type="confirmation.cancelled", action_id=record.action_id,
                 username=identity.username, detail={"confirmation_id": record.id})
    db.commit()
    return {"id": record.id, "status": record.status}


# ============================================== read-only history for the owner

def _action_summary(a: Action) -> dict:
    return {"id": a.id, "created_at": a.created_at.isoformat() if a.created_at else None,
            "user": a.username, "role": a.role, "agent": a.agent_id,
            "session": a.session_id, "user_request": a.user_request,
            "action": a.action_name, "resource": a.resource_name,
            "decision": a.decision, "blast_radius": a.blast_radius,
            "reversibility": a.reversibility, "trajectory": a.trajectory_score,
            "intent": a.intent_status, "authorized": a.authorized,
            "terms_category": a.terms_category, "proposal_source": a.proposal_source,
            "execution_status": a.execution_status,
            "verification_status": a.verification_status,
            "commit_status": a.commit_status}


@router.get("/actions")
def list_actions(limit: int = 50, db: Session = Depends(get_db),
                 identity: Identity = Depends(current_identity)):
    """A normal user sees only their own actions."""
    query = select(Action).order_by(Action.id.desc()).limit(limit)
    if identity.role not in OBSERVER_ROLES:
        query = query.where(Action.user_id == identity.user_id)
    return {"actions": [_action_summary(a) for a in db.scalars(query).all()]}


@router.get("/actions/{action_id}")
def get_action(action_id: int, db: Session = Depends(get_db),
               identity: Identity = Depends(current_identity)):
    action = db.get(Action, action_id)
    if action is None:
        raise HTTPException(status_code=404, detail="unknown action")
    if action.user_id != identity.user_id and identity.role not in OBSERVER_ROLES:
        raise HTTPException(status_code=404, detail="unknown action")
    return {**_action_summary(action), "analysis": action.analysis, "result": action.result}


# ==================================== ADMIN SECURITY TERMINAL - READ ONLY
# Every endpoint below is gated by require_observer. Nothing here can create,
# change, override or reverse an AEGIS decision. There is no write path.

@router.get("/admin/security/events")
def security_events(limit: int = 100, user: str = "", decision: str = "",
                    db: Session = Depends(get_db),
                    identity: Identity = Depends(require_observer)):
    query = select(Action).order_by(Action.id.desc())
    if user:
        query = query.where(Action.username == user)
    if decision:
        query = query.where(Action.decision == decision)
    rows = db.scalars(query.limit(limit)).all()
    return {"events": [_action_summary(a) for a in rows],
            "read_only": True,
            "note": "AEGIS automatically made every decision shown here."}


@router.get("/admin/security/events/{action_id}")
def security_event_detail(action_id: int, db: Session = Depends(get_db),
                          identity: Identity = Depends(require_observer)):
    action = db.get(Action, action_id)
    if action is None:
        raise HTTPException(status_code=404, detail="unknown security event")
    user = db.get(User, action.user_id)
    return {
        **_action_summary(action),
        "email": user.email if user else None,
        "analysis": action.analysis,
        "result": action.result,
        "read_only": True,
        "note": "AEGIS automatically made this decision. It cannot be changed here.",
    }


@router.get("/admin/security/users")
def security_users(db: Session = Depends(get_db),
                   identity: Identity = Depends(require_observer)):
    out = []
    for user in db.scalars(select(User).order_by(User.id)).all():
        last = db.scalar(select(Action).where(Action.user_id == user.id)
                         .order_by(Action.id.desc()).limit(1))
        events = db.scalar(select(func.count(Action.id))
                           .where(Action.user_id == user.id)) or 0
        denied = db.scalar(select(func.count(Action.id))
                           .where(Action.user_id == user.id,
                                  Action.decision == BLOCK)) or 0
        high = db.scalar(select(func.count(Action.id))
                         .where(Action.user_id == user.id,
                                Action.blast_radius >= 5.0)) or 0
        restriction = _restriction_for(db, user.id)
        out.append({
            "user_id": user.id, "username": user.username, "email": user.email,
            "role": user.role, "events": events, "denied": denied,
            "high_impact": high,
            "trajectory": last.trajectory_score if last else 0,
            "trajectory_level": (last.analysis.get("trajectory", {}).get("level")
                                 if last and last.analysis else "NORMAL"),
            "status": "RESTRICTED" if restriction else "NORMAL",
            "restriction_reason": restriction.reason if restriction else None,
            "restriction_expires": (restriction.expires_at.isoformat()
                                    if restriction else None),
        })
    return {"users": out, "read_only": True}


@router.get("/admin/security/users/{user_id}/trajectory")
def security_user_trajectory(user_id: int, db: Session = Depends(get_db),
                             identity: Identity = Depends(require_observer)):
    rows = db.scalars(select(Action).where(Action.user_id == user_id)
                      .order_by(Action.id.asc()).limit(200)).all()
    return {
        "user_id": user_id,
        "history": [{
            "action_id": a.id,
            "at": a.created_at.isoformat() if a.created_at else None,
            "action": a.action_name, "decision": a.decision,
            "score": a.trajectory_score,
            "level": (a.analysis.get("trajectory", {}).get("level")
                      if a.analysis else "NORMAL"),
            "signals": (a.analysis.get("trajectory", {}).get("signals", [])
                        if a.analysis else []),
        } for a in rows],
        "read_only": True,
    }


@router.get("/admin/security/overview")
def security_overview(db: Session = Depends(get_db),
                      identity: Identity = Depends(require_observer)):
    total = db.scalar(select(func.count(Action.id))) or 0
    counts = {d: db.scalar(select(func.count(Action.id))
                           .where(Action.decision == d)) or 0
              for d in (ALLOW, REQUIRE_CONFIRMATION, BLOCK)}
    bands = {c: db.scalar(select(func.count(Action.id))
                          .where(Action.terms_category == c)) or 0
             for c in ("NORMAL", "RISKY", "PRIVILEGED", "FORBIDDEN")}
    restricted = sum(1 for u in db.scalars(select(User)).all()
                     if _restriction_for(db, u.id))
    return {
        "generated_at": utc_now_iso(),
        "totals": {"actions": total, **{k.lower(): v for k, v in counts.items()},
                   "executed": db.scalar(select(func.count(Action.id))
                                         .where(Action.execution_status == "executed")) or 0,
                   "rolled_back": db.scalar(select(func.count(Action.id))
                                            .where(Action.commit_status == "rolled_back")) or 0,
                   "restricted_users": restricted},
        "terms_bands": bands,
        "audit": audit.verify_chain(db),
        "recent": [_action_summary(a) for a in
                   db.scalars(select(Action).order_by(Action.id.desc()).limit(12)).all()],
        "read_only": True,
        "decision_authority": "AEGIS",
    }


@router.get("/admin/security/audit")
def security_audit(limit: int = 150, db: Session = Depends(get_db),
                   identity: Identity = Depends(require_observer)):
    rows = db.scalars(select(ActionEvent).order_by(ActionEvent.id.desc()).limit(limit)).all()
    return {"events": [{
        "id": e.id, "timestamp": e.timestamp.isoformat() if e.timestamp else None,
        "action_id": e.action_id, "event_type": e.event_type, "user": e.username,
        "agent": e.agent_id, "session": e.session_id, "action": e.action_name,
        "resource": e.resource_name, "decision": e.decision, "detail": e.detail,
        "previous_hash": e.previous_hash, "current_hash": e.current_hash,
    } for e in rows], "chain": audit.verify_chain(db), "read_only": True}


# ============================================================ owner-scoped views

@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db),
              identity: Identity = Depends(current_identity)):
    scope = [] if identity.role in OBSERVER_ROLES else [Action.user_id == identity.user_id]
    total = db.scalar(select(func.count(Action.id)).where(*scope)) or 0
    blocked = db.scalar(select(func.count(Action.id))
                        .where(Action.decision == BLOCK, *scope)) or 0
    pending = db.scalar(select(func.count(ApprovalRequest.id))
                        .where(ApprovalRequest.status == "pending")) or 0
    executed = db.scalar(select(func.count(Action.id))
                         .where(Action.execution_status == "executed", *scope)) or 0
    rolled_back = db.scalar(select(func.count(Action.id))
                            .where(Action.commit_status == "rolled_back", *scope)) or 0
    high_risk = db.scalar(select(func.count(Action.id))
                          .where(Action.blast_radius >= 5.0, *scope)) or 0
    recent = db.scalars(select(Action).where(*scope)
                        .order_by(Action.id.desc()).limit(10)).all()
    my_last = db.scalar(select(Action).where(Action.user_id == identity.user_id)
                        .order_by(Action.id.desc()).limit(1))
    resources = db.scalars(select(Resource)).all()
    return {
        "generated_at": utc_now_iso(),
        "totals": {"actions": total, "blocked": blocked, "pending_approvals": pending,
                   "pending_confirmations": pending, "executed": executed,
                   "rolled_back": rolled_back, "high_risk": high_risk},
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
