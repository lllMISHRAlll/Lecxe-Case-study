from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.auth.tokens import InvalidTokenError, TokenService
from app.auth.users import DEMO_USERS
from app.core.clock import FixedClock

SECRET = "test-secret-0123456789abcdef0123456789"
NOW = datetime(2026, 11, 19, 9, 0, tzinfo=UTC)
USER = DEMO_USERS[0]


def service(now=NOW, secret=SECRET):
    return TokenService(secret=secret, ttl_hours=8, clock=FixedClock(now))


def test_auth_10_token_carries_identity_and_expires_in_8_hours():
    claims = service().decode(service().issue(USER))

    assert claims.user_id == USER.id
    assert claims.role == USER.role
    assert claims.name == USER.name
    assert claims.expires_at == NOW + timedelta(hours=8)


def test_auth_11_expired_token_is_rejected():
    token = service().issue(USER)

    with pytest.raises(InvalidTokenError):
        service(now=NOW + timedelta(hours=8, seconds=1)).decode(token)


def test_auth_12_tampered_signature_is_rejected():
    token = service().issue(USER)
    head, payload, sig = token.split(".")
    tampered = f"{head}.{payload}.{sig[:-2]}{'AA' if sig[-2:] != 'AA' else 'BB'}"

    with pytest.raises(InvalidTokenError):
        service().decode(tampered)


def test_auth_13_alg_none_is_rejected():
    payload = {"sub": USER.id, "role": USER.role.value, "name": USER.name,
               "exp": int((NOW + timedelta(hours=1)).timestamp())}
    unsigned = jwt.encode(payload, key="", algorithm="none")

    with pytest.raises(InvalidTokenError):
        service().decode(unsigned)


def test_auth_13_different_secret_is_rejected():
    token = service(secret="another-secret-0123456789abcdef0123").issue(USER)

    with pytest.raises(InvalidTokenError):
        service().decode(token)


def test_garbage_token_is_rejected():
    with pytest.raises(InvalidTokenError):
        service().decode("not-a-token")


def test_token_for_unknown_role_is_rejected():
    payload = {"sub": USER.id, "role": "admin", "name": "x",
               "exp": int((NOW + timedelta(hours=1)).timestamp())}
    token = jwt.encode(payload, SECRET, algorithm="HS256")

    with pytest.raises(InvalidTokenError):
        service().decode(token)
