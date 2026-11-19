"""Builds and holds the app's collaborators. Routes and graph nodes get them from here."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.api.rate_limit import RateLimiter
from app.auth.tokens import TokenService
from app.auth.users import UserDirectory
from app.core.clock import Clock, SystemClock
from app.core.config import Settings


@dataclass
class Container:
    settings: Settings
    clock: Clock = field(default_factory=SystemClock)
    users: UserDirectory = field(default_factory=UserDirectory)

    def __post_init__(self) -> None:
        self.tokens = TokenService(
            secret=self.settings.jwt_secret.get_secret_value(),
            ttl_hours=self.settings.jwt_ttl_hours,
            clock=self.clock,
        )
        self.limiter = RateLimiter(self.clock)
