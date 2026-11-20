"""Writes and payment actions get a clear refusal with the support email, and no LLM call."""

import pytest

from app.core.support import support_email
from app.llm.tasks import Task
from tests.graph.conftest import BO, PM, WM, base_script, events_of, run


def reply_of(events):
    return "".join(t["text"] for t in events_of(events, "token"))


@pytest.mark.parametrize("user,message", [
    (BO, "can you update the vendor name from Anand to Rocky"),
    (BO, "Can you make them inactive"),
    (PM, "Delete vendor Anand Engineering from the system."),
    (WM, "Delete all stock transactions older than a year."),
])
def test_write_requests_are_refused_with_the_support_email(make_service, user, message):
    service, llm, _ = make_service(base_script())
    reply = reply_of(run(service, user, message=message))
    assert "read data" in reply and support_email() in reply
    assert "open POs" not in reply  # no suggestion list
    assert llm.calls == []


@pytest.mark.parametrize("user", [PM, BO, WM])
def test_payment_actions_say_they_are_not_supported_and_give_the_support_email(
    make_service, user
):
    service, llm, _ = make_service(base_script())
    reply = reply_of(run(service, user, message="Release the advance payment for PO-2026-0002"))
    assert "payment" in reply.lower() and "not supported" in reply.lower()
    assert support_email() in reply
    assert llm.calls == []


def test_a_draft_edit_that_mentions_the_vendor_is_not_mistaken_for_a_write(make_service):
    service, llm, _ = make_service(base_script(**{
        Task.PO_EXTRACT: [{"vendor": "Zenith Steels"}, {"vendor": "Anand Engineering"}],
        Task.ROUTE: lambda s, u: {"intent": "raise_po", "confidence": 0.9, "reason": ""},
    }))
    first = run(service, PM, message="raise a po from Zenith Steels")
    cid = events_of(first, "conversation")[0]["conversation_id"]
    second = run(service, PM, conversation_id=cid, message="change the vendor to Anand Engineering")
    assert "read data" not in reply_of(second)
    assert len(llm.calls_for(Task.PO_EXTRACT)) == 2


def test_warehouse_manager_asking_for_payments_is_told_it_is_not_available_to_the_role(
    make_service,
):
    service, _, _ = make_service(base_script(**{
        Task.ROUTE: lambda s, u: {"intent": "analytics", "confidence": 0.95, "reason": ""},
        Task.SCHEMA_LINK: lambda s, u: {"answerable": False, "tables": [], "reason": "no access"},
    }))
    reply = reply_of(run(service, WM, message="Show me all the payment tranches for every PO"))
    assert "not available to your role" in reply
    assert "payments" not in reply.lower().replace("payment details", "")
    assert "stock" in reply


def test_other_unanswerable_questions_still_list_what_the_role_can_ask(make_service):
    service, _, _ = make_service(base_script(**{
        Task.ROUTE: lambda s, u: {"intent": "analytics", "confidence": 0.95, "reason": ""},
        Task.SCHEMA_LINK: lambda s, u: {"answerable": False, "tables": [], "reason": ""},
    }))
    reply = reply_of(run(service, PM, message="What colour is the warehouse roof?"))
    assert "payments" in reply
