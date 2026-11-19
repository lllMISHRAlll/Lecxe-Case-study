import logging

import pytest
from pydantic import ValidationError

from app.container import Container
from app.core.config import Settings
from app.llm.anthropic_llm import AnthropicLLM
from app.llm.heuristic import HeuristicLLM
from app.llm.openai_llm import OpenAILLM

OPENAI_KEY = "sk-proj-" + "a" * 40
ANTHROPIC_KEY = "sk-ant-api03-" + "b" * 40


def model_of(settings):
    return Container(settings=settings).language_model._inner


def test_openai_is_the_default_provider():
    assert Settings.model_fields["llm_provider"].default == "openai"
    assert isinstance(model_of(Settings(llm_provider="openai", openai_api_key=OPENAI_KEY)),
                      OpenAILLM)


def test_anthropic_provider_uses_the_anthropic_key_and_models():
    llm = model_of(Settings(llm_provider="anthropic", anthropic_api_key=ANTHROPIC_KEY,
                            openai_api_key=OPENAI_KEY))
    assert isinstance(llm, AnthropicLLM)
    assert (llm.fast_model, llm.strong_model) == ("claude-haiku-5-5", "claude-opus-5-5")


def test_anthropic_models_can_be_overridden():
    llm = model_of(Settings(llm_provider="anthropic", anthropic_api_key=ANTHROPIC_KEY,
                            anthropic_model_strong="claude-sonnet-5-5"))
    assert llm.strong_model == "claude-sonnet-5-5"


@pytest.mark.parametrize("provider", ["openai", "anthropic"])
def test_missing_key_for_the_selected_provider_falls_back_to_offline(provider, caplog):
    with caplog.at_level(logging.WARNING):
        assert isinstance(model_of(Settings(llm_provider=provider, openai_api_key="",
                                            anthropic_api_key="")), HeuristicLLM)
    assert provider.upper() in caplog.text


def test_fake_llm_wins_over_any_provider():
    assert isinstance(model_of(Settings(llm_provider="anthropic", fake_llm=True,
                                        anthropic_api_key=ANTHROPIC_KEY)), HeuristicLLM)


def test_unknown_provider_is_rejected():
    with pytest.raises(ValidationError):
        Settings(llm_provider="gemini")


def test_anthropic_key_in_the_openai_setting_is_reported(caplog):
    with caplog.at_level(logging.ERROR):
        model_of(Settings(llm_provider="openai", openai_api_key=ANTHROPIC_KEY))
    assert "looks like an Anthropic key" in caplog.text


def test_openai_key_in_the_anthropic_setting_is_reported(caplog):
    with caplog.at_level(logging.ERROR):
        model_of(Settings(llm_provider="anthropic", anthropic_api_key=OPENAI_KEY))
    assert "doesn't look like an Anthropic key" in caplog.text


def test_tracing_wraps_anthropic_calls_with_the_masked_client():
    settings = Settings(llm_provider="anthropic", anthropic_api_key=ANTHROPIC_KEY,
                        langsmith_tracing=True, langsmith_api_key="lsv2_pt_" + "c" * 40)
    llm = model_of(settings)
    assert llm.trace is not None
