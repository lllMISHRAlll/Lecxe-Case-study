import pytest

from app.agents.routing.rewriter import FollowUpRewriter, Turn, is_follow_up
from app.llm.fake import ScriptedLLM
from app.llm.tasks import Task

HISTORY = [
    Turn("Show spend by vendor", "Global Automation leads."),
    Turn("Only for August", "In August Zenith leads."),
    Turn("Which vendors are in Chennai?", "Anand Engineering."),
    Turn("How many open POs do they have?", "Two open POs."),
]


def test_rtr_01_standalone_question_skips_the_llm():
    llm = ScriptedLLM({})
    question = "Which warehouse holds the most stock right now?"

    assert FollowUpRewriter(llm).rewrite(question, HISTORY) == question
    assert llm.calls == []


def test_no_history_means_no_rewrite():
    llm = ScriptedLLM({})
    assert FollowUpRewriter(llm).rewrite("and last month?", []) == "and last month?"
    assert llm.calls == []


def test_rtr_02_follow_up_is_rewritten_using_only_the_last_three_turns():
    llm = ScriptedLLM({Task.REWRITE: [{"question": "How many open POs does Anand Engineering "
                                                   "have for last month?"}]})

    rewritten = FollowUpRewriter(llm).rewrite("and last month?", HISTORY)

    assert rewritten == "How many open POs does Anand Engineering have for last month?"
    prompt = llm.calls[0].user
    assert "How many open POs do they have?" in prompt
    assert "Only for August" in prompt
    assert "Show spend by vendor" not in prompt
    assert "and last month?" in prompt


def test_rewriter_failure_keeps_the_original_question():
    def broken(system, user):
        raise RuntimeError("down")

    assert FollowUpRewriter(ScriptedLLM({Task.REWRITE: broken})).rewrite(
        "what about them?", HISTORY) == "what about them?"


@pytest.mark.parametrize("text", ["and last month?", "what about Zenith?", "only open ones",
                                  "show them as a pie", "same for USD", "why?",
                                  "How about those vendors?"])
def test_follow_up_markers_are_detected(text):
    assert is_follow_up(text)


@pytest.mark.parametrize("text", ["Which warehouse holds the most stock right now?",
                                  "Show spend by vendor for August 2026",
                                  "List unexpected receipts that still need reconciling"])
def test_standalone_questions_are_not_follow_ups(text):
    assert not is_follow_up(text)
