from datetime import date
from decimal import Decimal

from app.po.slots import ExtractedLine, SlotExtraction
from evals.scoring import extraction_score, results_match


def test_results_match_ignores_order_aliases_and_extra_columns():
    reference = [["Zenith", Decimal("2")], ["Anand", Decimal("3")]]
    generated = [["Anand", 3, "Chennai"], ["Zenith", 2.0, "Delhi"]]
    assert results_match(reference, generated)


def test_results_match_rejects_wrong_values_or_counts():
    assert not results_match([["Zenith", 2]], [["Zenith", 3]])
    assert not results_match([["Zenith", 2]], [["Zenith", 2], ["Anand", 1]])
    assert results_match([[date(2026, 8, 1)]], [["2026-08-01"]])


def test_extraction_score_counts_matching_fields():
    got = SlotExtraction(vendor="Zenith Steels", lines=[
        ExtractedLine(item="MS tube 25x40", quantity=50, unit_price=125)])
    expected = {"vendor": "zenith", "items": ["ms tube"], "quantity": 50, "unit_price": 120}
    assert extraction_score(got, expected) == 0.75
    assert extraction_score(SlotExtraction(), {}) == 1.0
