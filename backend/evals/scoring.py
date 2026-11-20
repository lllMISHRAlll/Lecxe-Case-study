"""Scoring helpers for the evals. Deterministic and unit tested."""

from __future__ import annotations

from collections import Counter
from decimal import Decimal
from typing import Any


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
