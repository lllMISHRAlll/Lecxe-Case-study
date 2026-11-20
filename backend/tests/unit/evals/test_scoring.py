from datetime import date
from decimal import Decimal

from evals.scoring import results_match


def test_results_match_ignores_order_aliases_and_extra_columns():
    reference = [["Zenith", Decimal("2")], ["Anand", Decimal("3")]]
    generated = [["Anand", 3, "Chennai"], ["Zenith", 2.0, "Delhi"]]
    assert results_match(reference, generated)


def test_results_match_rejects_wrong_values_or_counts():
    assert not results_match([["Zenith", 2]], [["Zenith", 3]])
    assert not results_match([["Zenith", 2]], [["Zenith", 2], ["Anand", 1]])
    assert results_match([[date(2026, 8, 1)]], [["2026-08-01"]])
