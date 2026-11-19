import pytest

from app.domain.vocabulary import (
    CANONICAL_TERMS,
    CANONICAL_UNITS,
    PAYMENT_TERM_ALIASES,
    UNIT_ALIASES,
    canonical_term,
    canonical_unit,
)


@pytest.mark.parametrize(("raw", "expected"), [
    ("KG", "kg"), ("Kg", "kg"), ("kg", "kg"), ("Nos.", "pcs"), ("Nos", "pcs"), ("Unit", "pcs"),
    ("pcs", "pcs"), ("Set", "set"), ("Ltr", "ltr"), ("Mtr", "mtr"), ("mtr", "mtr"),
    ("Pair", "pair"), ("Roll", "roll"), (" KG ", "kg"),
])
def test_norm_10_unit_spellings_map_to_canonical(raw, expected):
    assert canonical_unit(raw) == expected


def test_norm_13_unknown_unit_is_not_mapped():
    assert canonical_unit("barrel") is None


def test_every_unit_alias_points_at_a_canonical_unit():
    assert set(UNIT_ALIASES.values()) <= CANONICAL_UNITS


@pytest.mark.parametrize(("raw", "expected"), [
    ("100% Payment Adavcne", "100% Advance"),
    ("100% Payment Against Dispatch", "100% Against Dispatch"),
    ("10 DAys PDC Against Dispatch", "10 Days PDC Against Dispatch"),
    ("10 Days PDC Agst Dispatch", "10 Days PDC Against Dispatch"),
    ("20% Adv & Balance 45 Days Credit", "20% Advance, Balance 45 Days Credit"),
    ("30% Adv, Bal Against Dispatch", "30% Advance, Balance Against Dispatch"),
    ("30% Advance, Bal Against Dispatch", "30% Advance, Balance Against Dispatch"),
    ("30 Days", "30 Days Credit"),
    ("50% Advance & 50% 30 Days Credit", "50% Advance, Balance 30 Days Credit"),
    ("50% Advance and Balance 30 Days Credit", "50% Advance, Balance 30 Days Credit"),
    ("50% Advance & Balance 50% 30 Days Credit", "50% Advance, Balance 30 Days Credit"),
    ("50% Advance & 50% Against Dispatch", "50% Advance, Balance Against Dispatch"),
    ("50% Adv, Bal Against Dispatch", "50% Advance, Balance Against Dispatch"),
])
def test_norm_11_payment_term_spellings_map_to_canonical(raw, expected):
    assert canonical_term(raw) == expected


@pytest.mark.parametrize("term", [
    "100% After Dispatch", "100% After Work Completion", "100% Against PI", "10 Days PDC",
    "10 Days PDC Cheque", "7 Days PDC Against Dispatch", "30 Days Credit", "100% Advance",
])
def test_norm_12_terms_marked_unchanged_stay_unchanged(term):
    assert canonical_term(term) == term
    assert term in CANONICAL_TERMS


def test_norm_13_unknown_term_is_returned_as_is():
    assert canonical_term("Barter") == "Barter"


def test_term_lookup_is_case_and_space_tolerant():
    assert canonical_term("  30 days credit ") == "30 Days Credit"


def test_every_term_alias_points_at_a_canonical_term():
    assert set(PAYMENT_TERM_ALIASES.values()) <= set(CANONICAL_TERMS)
