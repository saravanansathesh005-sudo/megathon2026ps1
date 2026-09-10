"""Server-side approvals: one-time, short-lived, bound to user + session + exact payload."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy.orm import Session

from app.config import get_settings
from app.logging_config import utc_now
from app.models import Action, ApprovalRequest
from app.security.identity import Identity
from app.security.policy import REQUIRE_ADMIN_APPROVAL
from app.security.registry import APPROVER_ROLES

settings = get_settings()


def create(db: Session, action: Action, identity: Identity, decision: str) -> ApprovalRequest:
    level = "admin_approval" if decision == REQUIRE_ADMIN_APPROVAL else "confirmation"
    request = ApprovalRequest(
        action_id=action.id,
        requester_user_id=identity.user_id,
        requester_session_id=identity.session_id,
        action_hash=action.action_hash,
        required_level=level,
        status="pending",
        created_at=utc_now(),
        expires_at=utc_now() + timedelta(seconds=settings.APPROVAL_TTL_SECONDS),
    )
    db.add(request)
    db.flush()
    return request


def can_decide(approval: ApprovalRequest, identity: Identity) -> tuple[bool, str]:
    """Who is allowed to act on this approval."""
    if approval.required_level == "admin_approval":
        if identity.role not in APPROVER_ROLES:
            return False, "admin approval requires role admin or security_admin"
        return True, "approver role satisfied"
    # Confirmation is the requester's own to give, in the same session.
    if identity.user_id != approval.requester_user_id:
        return False, "confirmation must be given by the requesting user"
    if identity.session_id != approval.requester_session_id:
        return False, "confirmation must be given in the requesting session"
    return True, "requester confirmed in the originating session"


def validate_for_execution(db: Session, approval: ApprovalRequest | None, action: Action,
                           identity: Identity,
                           current_hash: str | None = None) -> tuple[bool, str, str | None]:
    """Return (ok, reason, invariant_code)."""
    if approval is None:
        return False, "no approval on record for this action", "INV-004"
    if approval.status != "approved":
        return False, "approval status is " + approval.status, "INV-006"
    if approval.consumed:
        return False, "approval already used (replay rejected)", "INV-006"
    expires = approval.expires_at
    if expires is not None and expires.tzinfo is None:
        from datetime import timezone
        expires = expires.replace(tzinfo=timezone.utc)
    if expires is not None and expires < utc_now():
        return False, "approval expired", "INV-007"
    if approval.requester_user_id != identity.user_id:
        return False, "approval belongs to a different user", "INV-006"
    if approval.requester_session_id != identity.session_id:
        return False, "approval belongs to a different session", "INV-006"
    payload_hash = current_hash if current_hash is not None else action.action_hash
    if approval.action_hash != payload_hash:
        return False, "action payload changed after approval", "INV-006"
    return True, "approval valid", None
