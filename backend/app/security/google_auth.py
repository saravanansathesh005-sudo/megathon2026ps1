"""Google OAuth 2.0 authorization-code flow.

The client secret lives only on the backend. The browser never receives it, and the
browser never tells us who it is: identity comes from Google's token endpoint and is
verified against Google's published keys before we trust a single field.

Role is assigned by the backend. A `role` sent by any client is ignored everywhere.
"""

from __future__ import annotations

import json
import secrets
import urllib.error
import urllib.parse
import urllib.request

import jwt
from jwt import PyJWKClient

from app.config import get_settings

settings = get_settings()

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
ISSUERS = ("https://accounts.google.com", "accounts.google.com")

_jwk_client: PyJWKClient | None = None


class GoogleAuthError(RuntimeError):
    pass


def configured() -> bool:
    return bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)


def new_state() -> str:
    """CSRF token for the authorization request."""
    return secrets.token_urlsafe(24)


def authorization_url(state: str) -> str:
    if not configured():
        raise GoogleAuthError("Google OAuth is not configured on this server")
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    return AUTH_URL + "?" + urllib.parse.urlencode(params)


def _exchange_code(code: str) -> dict:
    data = urllib.parse.urlencode({
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }).encode()
    req = urllib.request.Request(
        TOKEN_URL, data=data, method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        raise GoogleAuthError("token exchange failed (" + str(exc.code) + ")") from exc
    except urllib.error.URLError as exc:
        raise GoogleAuthError("Google unreachable: " + str(exc.reason)) from exc


def verify_id_token(id_token: str) -> dict:
    """Verify signature, issuer, audience and expiry against Google's JWKS."""
    global _jwk_client
    if _jwk_client is None:
        _jwk_client = PyJWKClient(JWKS_URL)
    try:
        signing_key = _jwk_client.get_signing_key_from_jwt(id_token)
        claims = jwt.decode(
            id_token, signing_key.key, algorithms=["RS256"],
            audience=settings.GOOGLE_CLIENT_ID, issuer=list(ISSUERS),
        )
    except Exception as exc:  # noqa: BLE001 - any verification failure is a refusal
        raise GoogleAuthError("id_token verification failed: " + type(exc).__name__) from exc

    if not claims.get("email_verified"):
        raise GoogleAuthError("Google account email is not verified")
    return claims


def exchange(code: str) -> dict:
    """Authorization code -> verified identity claims."""
    tokens = _exchange_code(code)
    id_token = tokens.get("id_token")
    if not id_token:
        raise GoogleAuthError("Google response contained no id_token")
    claims = verify_id_token(id_token)
    return {
        "google_sub": claims["sub"],
        "email": claims["email"],
        "display_name": claims.get("name") or claims["email"].split("@")[0],
    }
