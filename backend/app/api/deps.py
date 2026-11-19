"""FastAPI dependencies shared by routes."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, Request

from app.auth.tokens import InvalidTokenError
from app.auth.users import User
from app.container import Container
from app.core.errors import Forbidden, Unauthenticated
from app.rbac.capabilities import Capability, has_capability


def get_container(request: Request) -> Container:
    return request.app.state.container


def current_user(request: Request) -> User:
    container: Container = request.app.state.container
    token = request.cookies.get(container.settings.cookie_name)
    if not token:
        raise Unauthenticated()
    try:
        claims = container.tokens.decode(token)
    except InvalidTokenError as exc:
        raise Unauthenticated() from exc
    user = container.users.get(claims.user_id)
    if user is None or user.role != claims.role:
        raise Unauthenticated()
    return user


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def require(capability: Capability) -> Callable[..., User]:
    """Dependency factory: the signed-in user, if their role has `capability`."""

    def dependency(user: User = Depends(current_user)) -> User:  # noqa: B008
        if not has_capability(user.role, capability):
            raise Forbidden()
        return user

    return dependency
