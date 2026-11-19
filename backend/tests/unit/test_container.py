import logging

from app.container import Container
from app.core.config import Settings
from app.llm.heuristic import HeuristicLLM


def test_anthropic_key_in_the_openai_setting_is_reported(caplog):
    settings = Settings(openai_api_key="sk-ant-api03-" + "x" * 40, fake_llm=False)
    with caplog.at_level(logging.ERROR):
        Container(settings=settings).language_model  # noqa: B018
    assert "looks like an Anthropic key" in caplog.text


def test_without_a_key_the_offline_model_is_used():
    llm = Container(settings=Settings(openai_api_key="", fake_llm=False)).language_model
    assert isinstance(llm._inner, HeuristicLLM)
