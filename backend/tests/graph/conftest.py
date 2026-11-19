"""Builds a chat service on the test database with a scripted LLM."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.agents.service import ChatRequest, ChatService
from app.auth.users import DEMO_USERS
from app.container import Container
from app.core.clock import FixedClock
from app.core.config import Settings
from app.llm.fake import ScriptedLLM
from app.llm.tasks import Task

PM, BO, WM = DEMO_USERS
NOW = datetime(2026, 11, 19, 9, 0, tzinfo=UTC)


def allow(system, user):
    return {"allowed": True, "category": "ok", "reason": ""}


def no_chart(system, user):
    return {"type": "table"}


def base_script(**overrides):
    script = {Task.GUARD: allow, Task.CHART: no_chart,
              Task.REWRITE: lambda s, u: {"question": u.rsplit("Latest message: ", 1)[-1]}}
    script.update(overrides)
    return script


@pytest.fixture
def make_service(fresh_db):
    def factory(script, **settings):
        llm = ScriptedLLM(script)
        container = Container(
            settings=Settings(app_env="test", fx_usd_inr=88.0, **settings),
            clock=FixedClock(NOW), db=fresh_db, llm=llm)
        return ChatService.from_container(container), llm, container

    return factory


def run(service, user, **request):
    return list(service.stream(user, ChatRequest(**request)))


def events_of(events, kind):
    return [e.data for e in events if e.event == kind]


def kinds(events):
    return [e.event for e in events]
