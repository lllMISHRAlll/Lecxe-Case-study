import pytest
from fastapi.testclient import TestClient

from app.container import Container
from app.core.config import Settings
from app.llm.fake import ScriptedLLM
from app.main import create_app
from tests.graph.conftest import NOW, base_script


@pytest.fixture
def chat_client(fresh_db, api_clock):
    def factory(script=None, **settings):
        llm = ScriptedLLM(script or base_script())
        container = Container(
            settings=Settings(app_env="test", jwt_secret="api-test-secret-0123456789abcdef0123",
                              fx_usd_inr=88.0, **settings),
            clock=api_clock, db=fresh_db, llm=llm)
        return TestClient(create_app(container=container)), llm

    return factory


__all__ = ["NOW"]
