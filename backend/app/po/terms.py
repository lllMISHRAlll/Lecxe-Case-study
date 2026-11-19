"""How each canonical payment term splits into payment tranches."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

DueBasis = Literal["advance", "dispatch", "credit"]


@dataclass(frozen=True)
class TrancheTemplate:
    stage: str
    percentage: Decimal
    is_advance: bool
    blocks_dispatch: bool
    due_basis: DueBasis
    due_offset_days: int


def _t(stage: str, pct: int, advance: bool, blocks: bool, basis: DueBasis,
       days: int) -> TrancheTemplate:
    return TrancheTemplate(stage, Decimal(pct), advance, blocks, basis, days)


def _single(term: str, basis: DueBasis, days: int = 0, *, blocks: bool = False,
            advance: bool = False) -> list[TrancheTemplate]:
    return [_t(term, 100, advance, blocks, basis, days)]


def _advance_then(pct: int, balance_stage: str, basis: DueBasis,
                  days: int = 0) -> list[TrancheTemplate]:
    return [_t("Advance", pct, True, True, "advance", 0),
            _t(balance_stage, 100 - pct, False, basis == "dispatch", basis, days)]


TERM_TRANCHES: dict[str, list[TrancheTemplate]] = {
    "100% Advance": [_t("Advance", 100, True, True, "advance", 0)],
    "100% Against PI": _single("100% Against PI", "advance", blocks=True, advance=True),
    "100% Against Dispatch": _single("100% Against Dispatch", "dispatch", blocks=True),
    "100% After Dispatch": _single("100% After Dispatch", "dispatch"),
    "100% After Work Completion": _single("100% After Work Completion", "credit"),
    "7 Days PDC Against Dispatch": _single("7 Days PDC Against Dispatch", "dispatch", 7,
                                           blocks=True),
    "10 Days PDC": _single("10 Days PDC", "credit", 10),
    "10 Days PDC Cheque": _single("10 Days PDC Cheque", "credit", 10),
    "10 Days PDC Against Dispatch": _single("10 Days PDC Against Dispatch", "dispatch", 10,
                                            blocks=True),
    "30 Days Credit": _single("30 Days Credit", "credit", 30),
    "20% Advance, Balance 45 Days Credit": _advance_then(20, "Balance 45 Days Credit",
                                                         "credit", 45),
    "30% Advance, Balance Against Dispatch": _advance_then(30, "Balance Against Dispatch",
                                                           "dispatch"),
    "50% Advance, Balance Against Dispatch": _advance_then(50, "Balance Against Dispatch",
                                                           "dispatch"),
    "50% Advance, Balance 30 Days Credit": _advance_then(50, "Balance 30 Days Credit",
                                                         "credit", 30),
}


def tranches_for(term: str) -> list[TrancheTemplate]:
    return TERM_TRANCHES[term]
