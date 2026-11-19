from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.core.clock import FixedClock
from app.core.config import Settings
from app.main import create_app
from tests.conftest import FROZEN_NOW


class MovableClock(FixedClock):
    def advance(self, **kwargs) -> None:
        self._moment = self._moment + timedelta(**kwargs)


@pytest.fixture
def api_clock():
    return MovableClock(FROZEN_NOW)


@pytest.fixture
def settings():
    return Settings(
        app_env="test",
        jwt_secret="api-test-secret-0123456789abcdef0123",
        demo_login_password="1234567890",
    )


@pytest.fixture
def make_client(api_clock, settings):
    def factory(**overrides):
        app = create_app(settings=settings.model_copy(update=overrides), clock=api_clock)
        return TestClient(app)

    return factory


@pytest.fixture
def client(make_client):
    return make_client()


def login(client, email="procurement@demo.local", password="1234567890"):
    return client.post("/api/auth/login", json={"email": email, "password": password})
