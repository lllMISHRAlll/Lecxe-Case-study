"""The Anthropic adapter, against a fake SDK client (no network)."""

from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from app.llm.anthropic_llm import AnthropicLLM
from app.llm.port import LLMOutputError, LLMRefusalError
from app.llm.tasks import Task


class Out(BaseModel):
    value: int


def block(kind, text=""):
    return SimpleNamespace(type=kind, text=text)


class FakeMessages:
    def __init__(self, *, parsed=None, content=None, stop_reason="end_turn", stream_text=()):
        self.calls = []
        self._parsed, self._content = parsed, content or []
        self._stop, self._stream_text = stop_reason, stream_text

    def parse(self, **kwargs):
        self.calls.append(("parse", kwargs))
        return SimpleNamespace(parsed_output=self._parsed, stop_reason=self._stop, content=[])

    def create(self, **kwargs):
        self.calls.append(("create", kwargs))
        return SimpleNamespace(content=self._content, stop_reason=self._stop)

    @contextmanager
    def stream(self, **kwargs):
        self.calls.append(("stream", kwargs))
        yield SimpleNamespace(
            text_stream=iter(self._stream_text),
            get_final_message=lambda: SimpleNamespace(stop_reason=self._stop))


def llm_with(messages, strong="claude-opus-5-5", fast="claude-haiku-5-5", trace=None):
    client = SimpleNamespace(beta=SimpleNamespace(messages=messages))
    return AnthropicLLM(client=client, fast_model=fast, strong_model=strong, trace=trace)


def test_structured_returns_the_parsed_model_with_the_fast_model_and_low_effort():
    messages = FakeMessages(parsed=Out(value=3))
    result = llm_with(messages).structured(Task.ROUTE, system="sys", user="hi", schema=Out)

    assert result == Out(value=3)
    kind, kwargs = messages.calls[0]
    assert kind == "parse"
    assert kwargs["model"] == "claude-haiku-5-5"
    assert kwargs["output_format"] is Out
    assert kwargs["system"] == "sys"
    assert kwargs["messages"] == [{"role": "user", "content": "hi"}]
    assert kwargs["output_config"] == {"effort": "low"}
    assert "fallbacks" not in kwargs  # no server-side fallback for Haiku
    assert "temperature" not in kwargs  # rejected by current models


def test_strong_tasks_use_the_strong_model_high_effort_and_server_side_fallbacks():
    messages = FakeMessages(content=[block("thinking"), block("text", "SELECT 1")])
    sql = llm_with(messages).text(Task.GENERATE_SQL, system="s", user="u")

    assert sql == "SELECT 1"
    kwargs = messages.calls[0][1]
    assert kwargs["model"] == "claude-opus-5-5"
    assert kwargs["output_config"] == {"effort": "high"}
    assert kwargs["fallbacks"] == "default"
    assert kwargs["betas"] == ["server-side-fallback-2026-07-01"]


def test_answers_use_medium_effort():
    messages = FakeMessages(stream_text=["Spend ", "is ", "high."])
    tokens = list(llm_with(messages).stream(Task.ANSWER, system="s", user="u"))

    assert tokens == ["Spend ", "is ", "high."]
    kind, kwargs = messages.calls[0]
    assert kind == "stream"
    assert kwargs["output_config"] == {"effort": "medium"}


def test_refusals_raise():
    with pytest.raises(LLMRefusalError):
        llm_with(FakeMessages(stop_reason="refusal")).text(Task.ANSWER, system="", user="")
    with pytest.raises(LLMRefusalError):
        llm_with(FakeMessages(stop_reason="refusal")).structured(
            Task.ROUTE, system="", user="", schema=Out)
    with pytest.raises(LLMRefusalError):
        list(llm_with(FakeMessages(stop_reason="refusal", stream_text=["x"])).stream(
            Task.ANSWER, system="", user=""))


def test_unparsed_structured_output_is_an_output_error():
    with pytest.raises(LLMOutputError):
        llm_with(FakeMessages(parsed=None)).structured(Task.ROUTE, system="", user="",
                                                       schema=Out)


def test_dict_output_is_validated_into_the_schema():
    messages = FakeMessages(parsed={"value": 9})
    assert llm_with(messages).structured(Task.ROUTE, system="", user="", schema=Out).value == 9


def test_calls_are_wrapped_by_the_tracer_when_given():
    wrapped = []

    def trace(name, fn):
        wrapped.append(name)
        return fn

    llm_with(FakeMessages(content=[block("text", "ok")]), trace=trace).text(
        Task.CHAT_REPLY, system="", user="")
    assert wrapped == ["llm.chat_reply"]


@pytest.mark.parametrize(("model", "has_fallback"), [
    ("claude-opus-5-5", True), ("claude-sonnet-5-5", True), ("claude-fable-5-2", True),
    ("claude-haiku-5-5", False), ("claude-haiku-4-5", False)])
def test_fallbacks_only_for_models_that_support_them(model, has_fallback):
    messages = FakeMessages(content=[block("text", "ok")])
    llm_with(messages, strong=model).text(Task.GENERATE_SQL, system="", user="")
    assert ("fallbacks" in messages.calls[0][1]) is has_fallback
