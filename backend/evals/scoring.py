"""Scoring helpers for the evals. Deterministic and unit tested."""

from __future__ import annotations

from collections import Counter
from decimal import Decimal
from typing import Any

from app.po.slots import SlotExtraction


def _norm(value: Any) -> str:
    if isinstance(value, Decimal | float | int) and not isinstance(value, bool):
        return f"{round(float(value), 2):g}"
    if hasattr(value, "isoformat"):
        return value.isoformat()[:10]
    return str(value).strip().lower()


def results_match(reference: list[list[Any]], generated: list[list[Any]]) -> bool:
    """Same number of rows, and every reference row's values appear in the matching
    generated row (extra columns in the generated result are fine; order doesn't matter)."""
    if len(reference) != len(generated):
        return False
    remaining = [Counter(_norm(v) for v in row) for row in generated]
    for row in sorted(reference, key=lambda r: [_norm(v) for v in r]):
        wanted = Counter(_norm(v) for v in row)
        for i, candidate in enumerate(remaining):
            if all(candidate[k] >= n for k, n in wanted.items()):
                remaining.pop(i)
                break
        else:
            return False
    return True


def extraction_score(got: SlotExtraction, expected: dict[str, Any]) -> float:
    """Share of expected fields the extraction got right (case-insensitive containment)."""
    checks: list[bool] = []
    first = got.lines[0] if got.lines else None
    for key, want in expected.items():
        if key == "vendor":
            checks.append(bool(got.vendor) and want in got.vendor.lower())
        elif key == "items":
            names = [(line.item or "").lower() for line in got.lines]
            checks.append(all(any(w in n for n in names) for w in want))
        elif key in ("quantity", "unit_price", "tax_percentage", "line", "action"):
            value = getattr(first, key, None) if first else None
            checks.append(value is not None and _norm(value) == _norm(want))
        elif key in ("payment_terms", "delivery_location"):
            checks.append(want in (getattr(got, key) or "").lower())
        elif key == "currency":
            checks.append(got.currency == want)
        elif key == "expected_delivery_date":
            checks.append(_norm(got.expected_delivery_date) == want)
    return sum(checks) / len(checks) if checks else 1.0
