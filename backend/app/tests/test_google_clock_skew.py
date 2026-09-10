"""Google sign-in must survive ordinary clock drift.

PyJWT refuses a token whose `iat` is even one second in the future. Google stamps
`iat` at the moment of issue, so a laptop running a few seconds behind fails every
sign-in with ImmatureSignatureError - which reads as a broken integration when it
is really a clock. These tests pin the leeway that absorbs it, and pin the limit
past which a token is still refused.
"""

from __future__ import annotations

import time

import jwt
import pytest

from app.security.google_auth import CLOCK_SKEW_LEEWAY

KEY = "test-signing-key"
AUD = "test-client-id"
ISS = "https://accounts.google.com"


def token(**claims) -> str:
    now = int(time.time())
    payload = {"iat": now, "exp": now + 3600, "aud": AUD, "iss": ISS}
    payload.update(claims)
    return jwt.encode(payload, KEY, algorithm="HS256")


def decode(raw: str, leeway: int = CLOCK_SKEW_LEEWAY) -> dict:
    return jwt.decode(raw, KEY, algorithms=["HS256"], audience=AUD, issuer=ISS,
                      leeway=leeway)


def test_the_leeway_is_large_enough_to_be_useful():
    assert CLOCK_SKEW_LEEWAY >= 60


@pytest.mark.parametrize("behind", [1, 5, 30, 90])
def test_a_host_running_behind_still_signs_in(behind):
    """The clock is slow, so Google's iat looks like the future."""
    assert decode(token(iat=int(time.time()) + behind))["aud"] == AUD


def test_without_leeway_even_one_second_fails():
    """Why the leeway exists at all - this is the bug it fixes."""
    with pytest.raises(jwt.ImmatureSignatureError):
        decode(token(iat=int(time.time()) + 5), leeway=0)


def test_skew_beyond_the_leeway_is_still_refused():
    with pytest.raises(jwt.ImmatureSignatureError):
        decode(token(iat=int(time.time()) + CLOCK_SKEW_LEEWAY + 60))


def test_an_expired_token_is_still_refused():
    now = int(time.time())
    with pytest.raises(jwt.ExpiredSignatureError):
        decode(token(iat=now - 7200, exp=now - CLOCK_SKEW_LEEWAY - 60))


def test_leeway_does_not_excuse_a_bad_signature():
    forged = jwt.encode({"iat": int(time.time()), "exp": int(time.time()) + 3600,
                         "aud": AUD, "iss": ISS}, "wrong-key", algorithm="HS256")
    with pytest.raises(jwt.InvalidSignatureError):
        decode(forged)


def test_leeway_does_not_excuse_a_wrong_audience():
    with pytest.raises(jwt.InvalidAudienceError):
        decode(token(aud="someone-elses-client-id"))


def test_leeway_does_not_excuse_a_wrong_issuer():
    with pytest.raises(jwt.InvalidIssuerError):
        decode(token(iss="https://evil.example.com"))
