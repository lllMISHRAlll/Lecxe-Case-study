"""Choosing several options at once, and the queue of questions behind the first one."""

import pytest
from pydantic import ValidationError

from app.agents.service import ChatRequest, POAction
from app.po.models import PODraft
from app.po.slots import Unresolved, apply_choice
from tests.fixtures.po_catalog import catalog

CAT = catalog()


def test_po_action_accepts_one_choice_or_a_list():
    assert POAction(type="choose", choice="item:i-nut").choice == "item:i-nut"
    action = POAction(type="choose", choices=["item:i-nut", "item:i-nut10"])
    assert action.choices == ["item:i-nut", "item:i-nut10"]
    ChatRequest(po_action=action)


def test_a_choose_action_needs_a_choice():
    with pytest.raises(ValidationError):
        POAction(type="choose")
    with pytest.raises(ValidationError):
        POAction(type="choose", choices=[])


def test_the_list_of_choices_is_bounded():
    with pytest.raises(ValidationError):
        POAction(type="choose", choices=[f"item:{n}" for n in range(21)])


def test_apply_choice_can_add_several_items_at_once():
    draft = PODraft(idempotency_key="k")
    out = apply_choice(draft, "item", ["i-nut", "i-nut10"], CAT)
    assert [ln.item.code for ln in out.lines] == ["BO-MC-0001", "BO-MC-0004"]
    assert [ln.position for ln in out.lines] == [1, 2]


def test_apply_choice_never_adds_an_item_twice():
    draft = apply_choice(PODraft(idempotency_key="k"), "item", ["i-nut"], CAT)
    out = apply_choice(draft, "item", ["i-nut", "i-nut10"], CAT, quantity="3")
    assert [ln.item.code for ln in out.lines] == ["BO-MC-0001", "BO-MC-0004"]
    assert float(out.lines[0].quantity) == 3.0  # the existing line is filled, not duplicated


def test_a_single_id_still_works_for_vendors():
    out = apply_choice(PODraft(idempotency_key="k"), "vendor", "v-anand", CAT)
    assert out.vendor.id == "v-anand"


def test_unresolved_round_trips_through_json_for_the_queue():
    first = Unresolved(kind="item", query="hex nut", pending={"quantity": "5"})
    assert Unresolved.model_validate(first.model_dump(mode="json")) == first
