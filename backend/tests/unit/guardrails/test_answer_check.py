import pytest

from app.guardrails.answer_check import check_answer_numbers, template_answer
from app.sql.executor import Column, QueryResult

RESULT = QueryResult(
    columns=[Column("vendor", "text"), Column("spend_inr", "number"), Column("pos", "number")],
    rows=[["Zenith Steels", 12900.0, 2], ["Anand Engineering", 3150.0, 2],
          ["Global Automation", 72160.0, 1]],
    truncated=False,
)


@pytest.mark.parametrize("answer", [
    "Global Automation leads with ₹72,160 across 1 PO.",
    "Zenith Steels spent ₹12,900.00 on 2 POs.",
    "Total spend is ₹88,210.",
    "Global Automation is 81.8% of spend.",
    "Global Automation accounts for about 82% of the total.",
    "3 vendors have spend.",
    "Top 3 vendors are shown.",
    "Zenith spent 12.9 thousand.",
    "In 2026 Zenith spent ₹12,900.",
])
def test_out_02_numbers_from_the_data_pass(answer):
    assert check_answer_numbers(answer, RESULT).ok, answer


@pytest.mark.parametrize("answer", [
    "Zenith spent ₹15,000.",
    "There are 42 vendors.",
    "Global Automation is 55% of spend.",
])
def test_out_02_invented_numbers_are_flagged(answer):
    check = check_answer_numbers(answer, RESULT)
    assert not check.ok
    assert check.unknown


def test_out_03_template_answer_uses_only_the_data():
    text = template_answer(RESULT)
    assert "3 rows" in text
    assert "Global Automation" in text or "Zenith Steels" in text


def test_template_answer_for_empty_result():
    empty = QueryResult(columns=[Column("vendor", "text")], rows=[], truncated=False)
    assert "No rows" in template_answer(empty)


SCORECARD = QueryResult(
    columns=[Column("vendor", "text"), Column("pos", "number"), Column("spend_inr", "number"),
             Column("fulfilment_pct", "number"), Column("on_time_pct", "number")],
    rows=[["Sterling Steels", 2, 3021209.47, 0.0, None],
          ["Meridian Engineering", 1, 395456.74, 102.4, 100.0],
          ["Summit Engineering", 2, 259384.14, 66.6, 0.0],
          ["Cobalt Engineering", 3, 120000.0, 100.0, 100.0],
          ["Anand Engineering", 1, 15322.0, 55.55, 50.0]],
    truncated=False,
)


@pytest.mark.parametrize("answer", [
    "Meridian Engineering is 102.4% fulfilled and 100% on time.",
    "Sterling Steels has 0% fulfilment so far.",
    "Average fulfilment is 64.91% and on-time delivery averages 62.5%.",
])
def test_percentages_already_in_the_data_pass(answer):
    assert check_answer_numbers(answer, SCORECARD).ok, answer


def test_invented_percentages_are_still_flagged():
    check = check_answer_numbers("Summit is 87% fulfilled.", SCORECARD)
    assert not check.ok and check.unknown == ["87%"]


def test_template_answer_skips_blank_values():
    text = template_answer(SCORECARD)
    assert "None" not in text
    assert "Sterling Steels" in text and "5 rows" in text


def test_shown_and_remaining_row_counts_are_allowed_when_given_as_context():
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    rows = [["Vendor " + letters[i % 26] * (1 + i // 26)] for i in range(34)]  # no digits
    result = QueryResult(columns=[Column("vendor", "text")], rows=rows, truncated=False)
    answer = "There are 34 vendors. The first 20 are listed; the other 14 are in the table."
    assert not check_answer_numbers(answer, result).ok
    assert check_answer_numbers(answer, result, context="shown 20 remaining 14").ok
