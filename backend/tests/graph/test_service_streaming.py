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
    def explode(*args, **kwargs):
        raise RuntimeError("secret internal detail")

    service, _, _ = make_service(base_script(**{Task.ANSWER: lambda s, u: "x"}))
    service.deps.executor.run = explode
    events = run(service, PM, button_id="pm_spend_by_vendor")
    errors = [e.data for e in events if e.event == "error"]
    assert errors and len(errors[0]["reference"]) == 8
    assert "secret internal detail" not in str(errors)
    assert events[-1].event == "done"


class AuthenticationError(Exception):
    """Same name as the OpenAI SDK's error, without importing the SDK."""


def test_answer_failure_falls_back_to_the_data_answer(make_service):
    def down(system, user):
        raise AuthenticationError("Incorrect API key provided")

    service, _, _ = make_service(base_script(**{Task.ANSWER: down}))
    events = run(service, PM, button_id="pm_spend_by_vendor")
    kinds = [e.event for e in events]
    assert "error" not in kinds
    replaced = [e.data["text"] for e in events if e.event == "answer_replace"]
    assert replaced and "5 rows" in replaced[0]


def test_small_talk_failure_falls_back_to_a_fixed_reply(make_service):
    def down(system, user):
        raise AuthenticationError("Incorrect API key provided")

    service, _, _ = make_service(base_script(**{Task.CHAT_REPLY: down}))
    events = run(service, PM, message="hi")
    assert "error" not in [e.event for e in events]
    reply = "".join(e.data["text"] for e in events if e.event == "token")
    assert "suggested questions" in reply


def test_ai_key_rejection_gets_a_clear_message(make_service):
    def down(system, user):
        raise AuthenticationError("Incorrect API key provided")

    service, _, _ = make_service(base_script(**{
        Task.ROUTE: lambda s, u: {"intent": "analytics", "confidence": 0.9, "reason": ""},
        Task.SCHEMA_LINK: down}))
    events = run(service, PM, message="Which vendors are overdue on deliveries?")
    error = next(e.data for e in events if e.event == "error")
    assert "AI service" in error["message"]
    assert "suggested questions" in error["message"]


def test_typed_question_with_the_ai_down_says_so(make_service):
    def down(system, user):
        raise AuthenticationError("Incorrect API key provided")

    service, _, _ = make_service(base_script(**{Task.ROUTE: down}))
    events = run(service, PM, message="Which vendors are overdue on deliveries?")
    error = next(e.data for e in events if e.event == "error")
    assert "AI service" in error["message"]
