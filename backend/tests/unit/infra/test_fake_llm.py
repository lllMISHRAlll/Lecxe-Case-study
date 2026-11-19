import pytest
from pydantic import BaseModel

from app.llm.fake import ScriptedLLM, ScriptExhaustedError
from app.llm.tasks import Task


class Answer(BaseModel):
    value: int


def test_returns_scripted_structured_response_and_records_prompt():
    llm = ScriptedLLM({Task.ROUTE: [Answer(value=1)]})

    result = llm.structured(Task.ROUTE, system="sys", user="hello", schema=Answer)

    assert result == Answer(value=1)
    assert llm.calls[0].task is Task.ROUTE
    assert llm.calls[0].system == "sys"
    assert llm.calls[0].user == "hello"


def test_scripted_responses_are_consumed_in_order():
    llm = ScriptedLLM({Task.GENERATE_SQL: ["select 1", "select 2"]})

    assert llm.text(Task.GENERATE_SQL, system="", user="") == "select 1"
    assert llm.text(Task.GENERATE_SQL, system="", user="") == "select 2"


def test_callable_script_receives_the_prompt():
    llm = ScriptedLLM({Task.ANSWER: lambda system, user: f"echo {user}"})

    assert llm.text(Task.ANSWER, system="", user="hi") == "echo hi"


def test_stream_yields_tokens_that_join_to_the_text():
    llm = ScriptedLLM({Task.ANSWER: ["Spend is high."]})

    tokens = list(llm.stream(Task.ANSWER, system="", user=""))

    assert len(tokens) > 1
    assert "".join(tokens) == "Spend is high."


def test_missing_script_raises():
    llm = ScriptedLLM({})

    with pytest.raises(ScriptExhaustedError):
        llm.text(Task.ROUTE, system="", user="")


def test_dict_response_is_validated_into_schema():
    llm = ScriptedLLM({Task.ROUTE: [{"value": 7}]})

    assert llm.structured(Task.ROUTE, system="", user="", schema=Answer).value == 7


def test_calls_for_filters_by_task():
    llm = ScriptedLLM({Task.ROUTE: ["a"], Task.ANSWER: ["b"]})
    llm.text(Task.ROUTE, system="", user="")
    llm.text(Task.ANSWER, system="", user="")

    assert [c.task for c in llm.calls_for(Task.ANSWER)] == [Task.ANSWER]
