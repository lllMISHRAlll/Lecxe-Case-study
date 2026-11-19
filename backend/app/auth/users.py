"""The three demo users. Defined in code on purpose (see PLAN.md section 4.1).

Only bcrypt hashes live here, never the plain password.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.auth.roles import Role

_DEMO_HASH = "$2b$12$GSOBsJpJYCGB0KYU/yNUQezUNPI6I9E2paN4zJ7kKwvCxxsaLNaiO"


class User(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    email: str
    name: str
    role: Role
    password_hash: str


DEMO_USERS: tuple[User, ...] = (
    User(id="0b0f6f43-6b63-4c43-9a51-6d1d3b6f0a01", email="procurement@demo.local",
         name="Arjun Rao", role=Role.PROCUREMENT_MANAGER, password_hash=_DEMO_HASH),
    User(id="0b0f6f43-6b63-4c43-9a51-6d1d3b6f0a02", email="owner@demo.local",
         name="Meera Iyer", role=Role.BUSINESS_OWNER, password_hash=_DEMO_HASH),
    User(id="0b0f6f43-6b63-4c43-9a51-6d1d3b6f0a03", email="warehouse@demo.local",
         name="Kabir Shah", role=Role.WAREHOUSE_MANAGER, password_hash=_DEMO_HASH),
)


class UserDirectory:
    """Lookup interface. Swap for a database-backed version later without touching callers."""

    def __init__(self, users: tuple[User, ...] = DEMO_USERS) -> None:
        self._by_email = {u.email.lower(): u for u in users}
        self._by_id = {u.id: u for u in users}

    def find_by_email(self, email: str) -> User | None:
        return self._by_email.get(email.strip().lower())

    def get(self, user_id: str) -> User | None:
        return self._by_id.get(user_id)

    def all(self) -> list[User]:
        return list(self._by_id.values())
