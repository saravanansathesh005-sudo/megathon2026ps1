"""Passwords, JWT, and the server-side identity used for every security decision.

Identity NEVER comes from the request body. It is resolved from the signed token.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import timedelta

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.logging_config import utc_now
from app.models import User, UserSession

settings = get_settings()
bearer = HTTPBearer(auto_error=False)


def hash_password(raw: str) -> str:
    return bcrypt.hashpw(raw.encode(), bcrypt.gensalt(rounds=8)).decode()


def verify_password(raw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(raw.encode(), hashed.encode())
    except ValueError:
        return False


def new_session_id() -> str:
    return uuid.uuid4().hex


def create_token(user: User, session_id: str, agent_id: str) -> str:
    now = utc_now()
    payload = {
        "sub": str(user.id),
        "username": user.username,
        "role": user.role,
        "sid": session_id,
        "agent": agent_id,
        "iat": now,
        "exp": now + timedelta(minutes=settings.TOKEN_TTL_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


@dataclass
class Identity:
    user_id: int
    username: str
    role: str
    session_id: str
    agent_id: str


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def current_identity(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> Identity:
    if creds is None:
        raise _unauthorized("missing bearer token")
    try:
        payload = jwt.decode(creds.credentials, settings.JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise _unauthorized("token expired")
    except jwt.PyJWTError:
        raise _unauthorized("invalid token")

    user = db.get(User, int(payload["sub"]))
    if user is None:
        raise _unauthorized("unknown user")

    sess = db.get(UserSession, payload["sid"])
    if sess is None or not sess.active:
        raise _unauthorized("session is not active")

    # Role comes from the database, never from the token body alone.
    return Identity(
        user_id=user.id,
        username=user.username,
        role=user.role,
        session_id=sess.id,
        agent_id=payload.get("agent", sess.agent_id),
    )


def authenticate(db: Session, username: str, password: str) -> User | None:
    user = db.scalar(select(User).where(User.username == username))
    if user is None or not verify_password(password, user.password_hash):
        return None
    return user
