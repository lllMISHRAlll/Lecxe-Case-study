import pytest

from app.agents.routing.router import Intent, IntentRouter
from app.llm.fake import ScriptedLLM
from app.llm.retry import RetryingLLM
from app.llm.tasks import Task


def router(*responses):
    llm = ScriptedLLM({Task.ROUTE: list(responses)})
    return IntentRouter(RetryingLLM(llm)), llm


def test_rtr_03_button_routes_to_canned_without_llm():
    r, llm = router()
    decision = r.route("", button_id="pm_open_pos")
    assert decision.intent is Intent.CANNED
    assert decision.source == "rule"
    assert llm.calls == []


def test_po_card_action_routes_to_po():
    r, llm = router()
    assert r.route("", po_action="confirm").intent is Intent.RAISE_PO
    assert llm.calls == []


@pytest.mark.parametrize(
    "text",
    [
        "Raise a PO for 50 MS tubes from Zenith",
        "create a purchase order for relays",
        "Please draft a new PO for Vanguard",
    ],
)
def test_po_keywords_route_to_po_without_llm(text):
    r, llm = router()
    assert r.route(text).intent is Intent.RAISE_PO
    assert llm.calls == []


@pytest.mark.parametrize(
    "text", ["hi", "Hello!", "thanks", "thank you!", "what can you do?", "help"]
)
def test_small_talk_routes_to_chat_without_llm(text):
    r, llm = router()
    assert r.route(text).intent is Intent.CHIT_CHAT
    assert llm.calls == []


def test_rtr_04_open_draft_sends_messages_to_the_po_flow():
    r, _ = router({"intent": "raise_po", "confidence": 0.7, "reason": "edit"})
    assert r.route("change price to 115", has_open_draft=True).intent is Intent.RAISE_PO


def test_rtr_04_open_draft_wins_when_classifier_is_unsure():
    r, _ = router({"intent": "analytics", "confidence": 0.6, "reason": "maybe"})
    assert r.route("50 of them", has_open_draft=True).intent is Intent.RAISE_PO


def test_rtr_05_cancel_while_draft_open_goes_to_po_flow_as_cancel():
    r, llm = router()
    decision = r.route("cancel", has_open_draft=True)
    assert decision.intent is Intent.RAISE_PO
    assert decision.po_command == "cancel"
    assert llm.calls == []


def test_rtr_05_clearly_different_question_leaves_the_po_flow():
    r, _ = router({"intent": "analytics", "confidence": 0.95, "reason": "data question"})
    assert r.route("Which vendors are overdue?", has_open_draft=True).intent is Intent.ANALYTICS


@pytest.mark.parametrize(
    ("label", "intent"),
    [
        ("analytics", Intent.ANALYTICS),
        ("raise_po", Intent.RAISE_PO),
        ("chit_chat", Intent.CHIT_CHAT),
        ("unclear", Intent.CLARIFY),
    ],
)
def test_rtr_06_classifier_labels_map_to_branches(label, intent):
    r, _ = router({"intent": label, "confidence": 0.9, "reason": ""})
    assert r.route("Something ambiguous about stock").intent is intent


def test_rtr_07_low_confidence_asks_to_clarify():
    r, _ = router({"intent": "analytics", "confidence": 0.3, "reason": "vague"})
    assert r.route("the thing from before").intent is Intent.CLARIFY


def test_rtr_08_invalid_output_twice_becomes_clarify():
    r, llm = router({"intent": "dance"}, {"confidence": "high"})
    assert r.route("stock stuff").intent is Intent.CLARIFY
    assert len(llm.calls) == 2


def test_classifier_prompt_contains_the_message():
    r, llm = router({"intent": "analytics", "confidence": 0.9, "reason": ""})
    r.route("Which vendors are overdue?")
    assert "Which vendors are overdue?" in llm.calls[0].user


def test_ai_service_failures_are_not_hidden_behind_a_clarifying_question():
    def broken(system, user):
        raise ConnectionError("network down")

    llm = ScriptedLLM({Task.ROUTE: broken})
    with pytest.raises(ConnectionError):
        IntentRouter(llm).route("stock stuff")


@pytest.mark.parametrize(
    "text",
    [
        "all 120",
        "120",
        "line 2: 85, line 3: 5100",
        "10 pcs and 2 k grams",
        "450 each",
        "use the last paid price",
        "yes",
        "same as last time",
        "all at 120",
        "₹5,124.50 for line 3",
    ],
)
def test_short_answers_to_an_open_draft_stay_in_the_po_flow_without_llm(text):
    r, llm = router()
    decision = r.route(text, has_open_draft=True, pending_question="What's the price per unit?")
    assert decision.intent is Intent.RAISE_PO
    assert decision.source == "rule"
    assert llm.calls == []


def test_a_real_question_during_a_draft_still_reaches_the_classifier_with_context():
    r, llm = router({"intent": "analytics", "confidence": 0.95, "reason": ""})
    decision = r.route(
        "Which vendors have overdue deliveries this month?",
        has_open_draft=True,
        pending_question="What's the price per unit for each?",
    )
    assert decision.intent is Intent.ANALYTICS
    prompt = llm.calls[0].user
    assert "purchase order draft is open" in prompt
    assert "What's the price per unit for each?" in prompt


def test_without_a_draft_short_numbers_are_not_forced_into_po():
    r, llm = router({"intent": "unclear", "confidence": 0.9, "reason": ""})
    assert r.route("all 120").intent is Intent.CLARIFY
    assert len(llm.calls) == 1
