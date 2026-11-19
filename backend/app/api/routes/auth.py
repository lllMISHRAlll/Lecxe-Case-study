from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field

from app.api.deps import client_ip, current_user, get_container
from app.auth.passwords import DUMMY_HASH, verify_password
from app.auth.users import User
from app.container import Container
from app.core.errors import InvalidCredentials

router = APIRouter(prefix="/auth", tags=["auth"])

ContainerDep = Annotated[Container, Depends(get_container)]
UserDep = Annotated[User, Depends(current_user)]


class LoginRequest(BaseModel):
    # Plain pattern: demo emails use the reserved .local domain, which strict validators reject.
    email: str = Field(pattern=r"^\s*[^@\s]+@[^@\s]+\.[^@\s]+\s*$", max_length=254)
    password: str = Field(max_length=128)


class UserOut(BaseModel):
    id: str
    name: str
    email: str
    role: str
    role_label: str

    @classmethod
    def of(cls, user: User) -> UserOut:
        return cls(id=user.id, name=user.name, email=user.email, role=user.role.value,
                   role_label=user.role.label)


class UserEnvelope(BaseModel):
    user: UserOut


class DemoUserOut(BaseModel):
    email: str
    name: str
    role: str
    role_label: str
    password: str | None


@router.get("/demo-users", response_model=list[DemoUserOut])
def demo_users(container: ContainerDep) -> list[DemoUserOut]:
    settings = container.settings
    secret = settings.demo_login_password
    password = secret.get_secret_value() if secret and settings.app_env != "prod" else None
    return [DemoUserOut(email=u.email, name=u.name, role=u.role.value, role_label=u.role.label,
                        password=password) for u in container.users.all()]


@router.post("/login", response_model=UserEnvelope)
def login(body: LoginRequest, request: Request, response: Response,
          container: ContainerDep) -> UserEnvelope:
    settings = container.settings
    container.limiter.hit("login", client_ip(request),
                          limit=settings.login_rate_limit_per_minute, window_seconds=60)
    user = container.users.find_by_email(body.email)
    password_ok = verify_password(body.password, user.password_hash if user else DUMMY_HASH)
    if user is None or not password_ok:
        raise InvalidCredentials()
    response.set_cookie(
        settings.cookie_name, container.tokens.issue(user), max_age=container.tokens.ttl_seconds,
        httponly=True, samesite="lax", secure=settings.cookie_secure, path="/",
    )
    return UserEnvelope(user=UserOut.of(user))


@router.get("/me", response_model=UserEnvelope)
def me(user: UserDep) -> UserEnvelope:
    return UserEnvelope(user=UserOut.of(user))


@router.post("/logout", status_code=204)
def logout(response: Response, container: ContainerDep) -> Response:
    response.delete_cookie(container.settings.cookie_name, path="/", httponly=True,
                           samesite="lax", secure=container.settings.cookie_secure)
    response.status_code = 204
    return response
