"""Canonical units and payment terms. Single source of truth for data cleaning and PO entry."""

from __future__ import annotations

import re

CANONICAL_UNITS = frozenset({"pcs", "kg", "set", "roll", "pair", "mtr", "ltr"})

# Raw spelling (lower case, trimmed) -> canonical unit.
UNIT_ALIASES: dict[str, str] = {
    **{u: u for u in CANONICAL_UNITS},
    "nos.": "pcs", "nos": "pcs", "no.": "pcs", "no": "pcs", "unit": "pcs", "units": "pcs",
    "pc": "pcs", "piece": "pcs", "pieces": "pcs",
    "kgs": "kg", "kilogram": "kg",
    "sets": "set", "ltrs": "ltr", "litre": "ltr", "liter": "ltr",
    "mtrs": "mtr", "meter": "mtr", "metre": "mtr", "m": "mtr",
    "pairs": "pair", "rolls": "roll",
}

CANONICAL_TERMS: tuple[str, ...] = (
    "100% Advance",
    "100% Against PI",
    "100% Against Dispatch",
    "100% After Dispatch",
    "100% After Work Completion",
    "7 Days PDC Against Dispatch",
    "10 Days PDC",
    "10 Days PDC Cheque",
    "10 Days PDC Against Dispatch",
    "30 Days Credit",
    "20% Advance, Balance 45 Days Credit",
    "30% Advance, Balance Against Dispatch",
    "50% Advance, Balance Against Dispatch",
    "50% Advance, Balance 30 Days Credit",
)

# Labels used on individual payment tranches (proc_po_payment_tranches.stage) besides terms.
STAGE_LABELS: tuple[str, ...] = (
    "Advance", "Balance Against Dispatch", "Balance 30 Days Credit", "Balance 45 Days Credit",
)

# Raw spelling (normalised key) -> canonical term. Only clear-cut synonyms and typos.
PAYMENT_TERM_ALIASES: dict[str, str] = {
    "100% payment adavcne": "100% Advance",
    "100% payment advance": "100% Advance",
    "100% payment against dispatch": "100% Against Dispatch",
    "10 days pdc agst dispatch": "10 Days PDC Against Dispatch",
    "20% adv & balance 45 days credit": "20% Advance, Balance 45 Days Credit",
    "30% adv, bal against dispatch": "30% Advance, Balance Against Dispatch",
    "30% advance, bal against dispatch": "30% Advance, Balance Against Dispatch",
    "30 days": "30 Days Credit",
    "50% advance & 50% 30 days credit": "50% Advance, Balance 30 Days Credit",
    "50% advance and balance 30 days credit": "50% Advance, Balance 30 Days Credit",
    "50% advance & balance 50% 30 days credit": "50% Advance, Balance 30 Days Credit",
    "50% advance & 50% against dispatch": "50% Advance, Balance Against Dispatch",
    "50% adv, bal against dispatch": "50% Advance, Balance Against Dispatch",
}


def term_key(raw: str) -> str:
    return re.sub(r"\s+", " ", raw.strip()).lower()


def term_lookup(include_stages: bool = False) -> dict[str, str]:
    """Every known spelling (normalised key) -> canonical value."""
    known = {term_key(t): t for t in CANONICAL_TERMS}
    if include_stages:
        known |= {term_key(s): s for s in STAGE_LABELS}
    return known | PAYMENT_TERM_ALIASES


def canonical_unit(raw: str) -> str | None:
    return UNIT_ALIASES.get(raw.strip().lower())


def canonical_term(raw: str) -> str:
    return term_lookup().get(term_key(raw), raw)
