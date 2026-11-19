"""Signed session tokens (JWT, HS256). Expiry is checked against the injected clock."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
from pydantic import BaseModel

from app.auth.roles import Role
from app.auth.users import User
from app.core.clock import Clock

_ALGORITHM = "HS256"


class InvalidTokenError(Exception):
    pass


class Claims(BaseModel):
    user_id: str
    role: Role
    name: str
    expires_at: datetime


class TokenService:
    def __init__(self, *, secret: str, ttl_hours: int, clock: Clock) -> None:
        self._secret = secret
        self._ttl = timedelta(hours=ttl_hours)
        self._clock = clock

    @property
    def ttl_seconds(self) -> int:
        return int(self._ttl.total_seconds())

    def issue(self, user: User) -> str:
        expires = self._clock.now() + self._ttl
        payload = {"sub": user.id, "role": user.role.value, "name": user.name,
                   "exp": int(expires.timestamp())}
        return jwt.encode(payload, self._secret, algorithm=_ALGORITHM)

    def decode(self, token: str) -> Claims:
        try:
            payload = jwt.decode(token, self._secret, algorithms=[_ALGORITHM],
                                 options={"verify_exp": False, "require": ["exp", "sub"]})
            claims = Claims(user_id=payload["sub"], role=Role(payload["role"]),
                            name=payload["name"],
                            expires_at=datetime.fromtimestamp(payload["exp"], tz=UTC))
        except (jwt.PyJWTError, KeyError, ValueError) as exc:
            raise InvalidTokenError("Invalid session token") from exc
        if claims.expires_at < self._clock.now():
            raise InvalidTokenError("Session expired")
        return claims
