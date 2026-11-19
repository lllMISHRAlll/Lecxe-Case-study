"""Exact PO arithmetic: Decimal, rounded half-up to two places per line."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.po.models import POLine

CENT = Decimal("0.01")
ZERO = Decimal("0.00")


@dataclass(frozen=True)
class Totals:
    subtotal: Decimal
    tax: Decimal
    total: Decimal


def _round(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def line_totals(line: POLine) -> Totals:
    if line.quantity is None or line.unit_price is None:
        return Totals(ZERO, ZERO, ZERO)
    subtotal = _round(line.quantity * line.unit_price)
    tax = _round(subtotal * line.tax_percentage / 100)
    return Totals(subtotal, tax, subtotal + tax)


def draft_totals(lines: Iterable[POLine]) -> Totals:
    parts = [line_totals(line) for line in lines]
    return Totals(sum((p.subtotal for p in parts), ZERO), sum((p.tax for p in parts), ZERO),
                  sum((p.total for p in parts), ZERO))
