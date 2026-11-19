from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.po.models import PODraft, POLine
from app.po.rules import apply_defaults, next_question, review
from tests.fixtures.po_catalog import catalog

TODAY = date(2026, 11, 19)
CAT = catalog()


def draft(**kw):
    return PODraft(idempotency_key="k", **kw)


def item(code):
    return next(i for i in CAT.items if i.code == code)


def vendor(vid):
    return next(v for v in CAT.vendors if v.id == vid)


def test_po_03_defaults_are_applied_and_shown():
    d = draft(vendor=vendor("v-anand"),
              lines=[POLine(position=1, item=item("RM-MT-0001"), quantity=Decimal(5),
                            unit_price=Decimal(80))])
    d = apply_defaults(d, TODAY)
    assert d.status == "open"
    assert d.currency == "INR"
    assert d.placed_on == TODAY
    assert d.payment_terms == "30 Days Credit"
    assert d.lines[0].unit == "kg"
    assert d.lines[0].tax_percentage == Decimal(0)
    assert "Payment terms set to the vendor's usual: 30 Days Credit" in review(d).defaults_used


def test_po_04_payment_terms_required_when_vendor_has_none():
    d = apply_defaults(draft(vendor=vendor("v-summit"), lines=[
        POLine(position=1, item=item("BO-MC-0001"), quantity=Decimal(5), unit_price=Decimal(3))
    ]), TODAY)
    assert d.payment_terms is None
    assert review(d).missing == ["payment_terms"]


@pytest.mark.parametrize("field", ["quantity", "unit_price"])
@pytest.mark.parametrize("value", ["0", "-1"])
def test_po_05_non_positive_quantity_or_price_is_rejected(field, value):
    with pytest.raises(ValidationError):
        POLine(position=1, item=item("BO-MC-0001"), **{field: Decimal(value)})


def test_po_06_inactive_vendor_or_item_is_an_error():
    d = draft(vendor=vendor("v-old"), lines=[POLine(position=1, item=item("BO-MC-0003"),
                                                     quantity=Decimal(1),
                                                     unit_price=Decimal(1))])
    errors = review(apply_defaults(d, TODAY)).errors
    assert any("Old Traders" in e for e in errors)
    assert any("Old Bracket" in e for e in errors)


def test_po_07_different_unit_is_allowed_with_a_warning():
    d = apply_defaults(draft(vendor=vendor("v-anand"), lines=[
        POLine(position=1, item=item("BO-MC-0001"), quantity=Decimal(2), unit="KG",
               unit_price=Decimal(250))]), TODAY)
    assert d.lines[0].unit == "kg"
    assert review(d).line_warnings[1] == ["Unit kg differs from the stock unit pcs."]


def test_unknown_unit_is_an_error():
    d = apply_defaults(draft(vendor=vendor("v-anand"), lines=[
        POLine(position=1, item=item("BO-MC-0001"), quantity=Decimal(2), unit="barrel",
               unit_price=Decimal(250))]), TODAY)
    assert any("barrel" in e for e in review(d).errors)


def test_unknown_payment_term_is_an_error_but_spellings_are_normalised():
    base = dict(vendor=vendor("v-anand"), lines=[POLine(position=1, item=item("BO-MC-0001"),
                                                        quantity=Decimal(2),
                                                        unit_price=Decimal(5))])
    assert apply_defaults(draft(payment_terms="30 days", **base), TODAY).payment_terms == \
        "30 Days Credit"
    bad = apply_defaults(draft(payment_terms="Barter", **base), TODAY)
    assert any("Barter" in e for e in review(bad).errors)


def test_po_13_missing_details_asked_one_at_a_time_in_order():
    d = draft()
    assert next_question(review(d)).slot == "vendor"
    d = draft(vendor=vendor("v-summit"))
    assert next_question(review(d)).slot == "item"
    d.lines.append(POLine(position=1, item=item("BO-MC-0001")))
    assert next_question(review(apply_defaults(d, TODAY))).slot == "quantity"
    d.lines[0].quantity = Decimal(10)
    assert next_question(review(apply_defaults(d, TODAY))).slot == "unit_price"
    d.lines[0].unit_price = Decimal(3)
    question = next_question(review(apply_defaults(d, TODAY)))
    assert question.slot == "payment_terms"
    assert "30 Days Credit" in [o.label for o in question.options]
    d.payment_terms = "30 Days Credit"
    assert next_question(review(apply_defaults(d, TODAY))) is None


def test_question_names_the_line_it_is_about():
    d = apply_defaults(draft(vendor=vendor("v-anand"), lines=[
        POLine(position=1, item=item("BO-MC-0001"), quantity=Decimal(1), unit_price=Decimal(1)),
        POLine(position=2, item=item("BO-MC-0002"), quantity=Decimal(1))]), TODAY)
    question = next_question(review(d))
    assert question.slot == "unit_price"
    assert question.line == 2
    assert "Hinge Set" in question.text


def test_contract_shape_uses_strings_for_money():
    d = apply_defaults(draft(vendor=vendor("v-anand"), lines=[
        POLine(position=1, item=item("RM-MT-0001"), quantity=Decimal(50),
               unit_price=Decimal(120))]), TODAY)
    out = d.to_contract(review(d))
    assert out["total_amount"] == "6000.00"
    assert out["lines"][0]["line_total"] == "6000.00"
    assert out["lines"][0]["quantity"] == "50"
    assert out["vendor"] == {"id": "v-anand", "name": "Anand Engineering Pvt. Ltd."}
    assert out["missing"] == []
    assert out["placed_on"] == "2026-11-19"
