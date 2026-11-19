"""SSE-05 and request handling at the service level."""

import pytest
from sqlalchemy import text

from app.agents.service import ChatRequest
from app.core.errors import NotFound
from app.llm.tasks import Task
from tests.graph.conftest import BO, PM, base_script, run


def test_sse_05_closing_the_stream_stops_the_run(make_service, fresh_db):
    service, _, _ = make_service(base_script(**{Task.ANSWER: lambda s, u: "x"}))
    stream = service.stream(PM, ChatRequest(button_id="pm_spend_by_vendor"))
    next(stream)  # conversation
    next(stream)  # first step
    stream.close()
    with fresh_db.read_engine.connect() as conn:
        assert conn.execute(text("select count(*) from assistant.messages "
                                 "where sender = 'assistant'")).scalar() == 0


def test_other_users_conversation_is_not_found(make_service):
    service, _, _ = make_service(base_script(**{Task.ANSWER: lambda s, u: "x"}))
    events = run(service, PM, button_id="pm_spend_by_vendor")
    conversation_id = events[0].data["conversation_id"]
    with pytest.raises(NotFound):
        list(service.stream(BO, ChatRequest(conversation_id=conversation_id, message="hi")))


def test_another_roles_button_is_forbidden_before_streaming(make_service):
    from app.core.errors import Forbidden

    service, _, _ = make_service(base_script())
    with pytest.raises(Forbidden):
        list(service.stream(BO, ChatRequest(button_id="pm_spend_by_vendor")))


def test_request_needs_exactly_one_kind_of_input():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ChatRequest()
    with pytest.raises(ValidationError):
        ChatRequest(message="hi", button_id="x")


def test_unexpected_error_becomes_an_error_event(make_service):
    def explode(system, user):
        raise RuntimeError("secret internal detail")

    service, _, _ = make_service(base_script(**{Task.ANSWER: explode}))
    events = run(service, PM, button_id="pm_spend_by_vendor")
    errors = [e.data for e in events if e.event == "error"]
    assert errors and len(errors[0]["reference"]) == 8
    assert "secret internal detail" not in str(errors)
    assert events[-1].event == "done"
