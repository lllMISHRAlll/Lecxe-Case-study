import pytest
from pydantic import BaseModel

from app.llm.fake import ScriptedLLM
from app.llm.port import LLMOutputError
from app.llm.retry import RetryingLLM
from app.llm.tasks import Task


class Out(BaseModel):
    value: int


def test_out_01_invalid_output_is_retried_once():
    inner = ScriptedLLM({Task.ROUTE: [{"value": "not a number"}, {"value": 3}]})
    assert RetryingLLM(inner).structured(Task.ROUTE, system="", user="", schema=Out).value == 3
    assert len(inner.calls) == 2


def test_out_01_second_failure_raises_llm_output_error():
    inner = ScriptedLLM({Task.ROUTE: [{"value": "x"}, {"value": "y"}]})
    with pytest.raises(LLMOutputError):
        RetryingLLM(inner).structured(Task.ROUTE, system="", user="", schema=Out)


def test_text_and_stream_pass_through():
    inner = ScriptedLLM({Task.ANSWER: ["one two", "three"]})
    llm = RetryingLLM(inner)
    assert llm.text(Task.ANSWER, system="", user="") == "one two"
    assert "".join(llm.stream(Task.ANSWER, system="", user="")) == "three"
