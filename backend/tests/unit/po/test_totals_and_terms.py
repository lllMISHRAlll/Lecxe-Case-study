from decimal import Decimal

import pytest

from app.domain.vocabulary import CANONICAL_TERMS
from app.po.models import ItemRef, POLine
from app.po.terms import tranches_for
from app.po.totals import draft_totals, line_totals

TUBE = ItemRef(id="i", code="C", name="Tube", unit="kg")


def line(qty, price, tax="0"):
    return POLine(position=1, item=TUBE, quantity=Decimal(qty), unit="kg",
                  unit_price=Decimal(price), tax_percentage=Decimal(tax))


def test_po_01_line_totals_with_two_place_rounding():
    totals = line_totals(line("3", "33.335", "18"))
    assert totals.subtotal == Decimal("100.01")
    assert totals.tax == Decimal("18.00")
    assert totals.total == Decimal("118.01")


def test_po_02_header_totals_sum_the_lines():
    totals = draft_totals([line("50", "120"), line("10", "450", "18")])
    assert (totals.subtotal, totals.tax, totals.total) == (
        Decimal("10500.00"), Decimal("810.00"), Decimal("11310.00"))


def test_incomplete_lines_count_as_zero():
    incomplete = POLine(position=1, item=TUBE, quantity=None, unit="kg", unit_price=None)
    assert draft_totals([incomplete]).total == Decimal("0.00")


@pytest.mark.parametrize("term", CANONICAL_TERMS)
def test_po_08_every_canonical_term_has_tranches_summing_to_100(term):
    tranches = tranches_for(term)
    assert tranches
    assert sum(t.percentage for t in tranches) == Decimal("100")
    assert all(t.due_basis in {"advance", "dispatch", "credit"} for t in tranches)


@pytest.mark.parametrize(("term", "expected"), [
    ("100% Advance", [("Advance", 100, True, True, "advance", 0)]),
    ("30 Days Credit", [("30 Days Credit", 100, False, False, "credit", 30)]),
    ("10 Days PDC Against Dispatch",
     [("10 Days PDC Against Dispatch", 100, False, True, "dispatch", 10)]),
    ("50% Advance, Balance 30 Days Credit",
     [("Advance", 50, True, True, "advance", 0),
      ("Balance 30 Days Credit", 50, False, False, "credit", 30)]),
    ("20% Advance, Balance 45 Days Credit",
     [("Advance", 20, True, True, "advance", 0),
      ("Balance 45 Days Credit", 80, False, False, "credit", 45)]),
])
def test_po_08_tranche_details(term, expected):
    got = [(t.stage, t.percentage, t.is_advance, t.blocks_dispatch, t.due_basis,
            t.due_offset_days) for t in tranches_for(term)]
    assert got == [(s, Decimal(p), a, b, d, o) for s, p, a, b, d, o in expected]


def test_unknown_term_has_no_tranches():
    with pytest.raises(KeyError):
        tranches_for("Barter")
