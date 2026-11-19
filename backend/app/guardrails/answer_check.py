"""Soft check that numbers stated in an answer come from the data.

Allowed: every number in the rows (including numbers inside text cells), column totals,
averages, the row count, and each value's share of its column total as a percentage.
A percentage may also match a value or average directly, for columns that hold percentages.
Rounding and 'thousand / lakh / crore / million' scales are tolerated.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.sql.executor import QueryResult

_NUMBER = re.compile(
    r"(?<![\w.-])[₹$]?\s?(?P<num>\d{1,3}(?:,\d{2,3})+|\d+)(?P<dec>\.\d+)?"
    r"(?:\s?(?P<scale>%|k\b|thousand|lakhs?|crores?|million|mn\b))?(?![\w-])", re.I)
_SCALES = {"k": 1e3, "thousand": 1e3, "lakh": 1e5, "lakhs": 1e5, "crore": 1e7, "crores": 1e7,
           "million": 1e6, "mn": 1e6}


@dataclass(frozen=True)
class AnswerCheck:
    ok: bool
    unknown: list[str]


def _numbers_in_text(text: str) -> list[tuple[float, bool, str]]:
    found = []
    for m in _NUMBER.finditer(text):
        value = float(m.group("num").replace(",", "") + (m.group("dec") or ""))
        scale = (m.group("scale") or "").lower()
        if scale and scale != "%":
            value *= _SCALES[scale]
        found.append((value, scale == "%", m.group(0).strip()))
    return found


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float | Decimal):
        return float(value)
    return None


def _allowed(result: QueryResult) -> tuple[set[float], set[float]]:
    plain: set[float] = {float(result.row_count)}
    percents: set[float] = {100.0}
    for col_index in range(len(result.columns)):
        values = [_as_float(row[col_index]) for row in result.rows]
        numbers = [v for v in values if v is not None]
        for row in result.rows:
            cell = row[col_index]
            if isinstance(cell, str):
                plain.update(v for v, _, _ in _numbers_in_text(cell))
        if not numbers:
            continue
        total = sum(numbers)
        plain.update(numbers)
        plain.update({total, total / len(numbers)})
        if total:
            percents.update(v / total * 100 for v in numbers)
    return plain, percents


def _close(value: float, candidates: set[float]) -> bool:
    return any(abs(value - c) <= max(abs(c) * 0.01, 0.5) for c in candidates)


def check_answer_numbers(answer: str, result: QueryResult, context: str = "") -> AnswerCheck:
    """`context` (question, notes such as latest data dates) may also supply numbers."""
    plain, percents = _allowed(result)
    plain.update(v for v, _, _ in _numbers_in_text(context))
    plain.update(float(n) for n in re.findall(r"\d+", context))
    unknown = []
    for value, is_percent, raw in _numbers_in_text(answer):
        if is_percent:
            # A percentage may be a share of a total, or a value already in a % column.
            if not (_close(value, percents) or _close(value, plain)):
                unknown.append(raw)
        elif not (_close(value, plain) or (1900 <= value <= 2100 and value.is_integer())):
            unknown.append(raw)
    return AnswerCheck(ok=not unknown, unknown=unknown)


def template_answer(result: QueryResult) -> str:
    """A plain answer built only from the data, used when the LLM answer fails the check."""
    if not result.rows:
        return "No rows matched your question."
    first = result.records()[0]
    details = ", ".join(f"{k} {v}" for k, v in first.items() if v is not None)
    more = " (showing the first 500)" if result.truncated else ""
    return (f"Here's what the data shows: {result.row_count} rows{more}. The first one is "
            f"{details}. See the table for the full result.")
