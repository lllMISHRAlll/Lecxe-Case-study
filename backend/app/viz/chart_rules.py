"""Picks a chart for a result. Fixed rules first; the LLM only when the rules can't decide."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field

from app.llm.port import LLM
from app.llm.tasks import Task
from app.sql.canned import ChartHint
from app.sql.executor import QueryResult

log = logging.getLogger(__name__)

ChartType = Literal["bar", "horizontal_bar", "line", "pie", "scatter", "table"]

MAX_PIE_SLICES = 6
MAX_VERTICAL_BARS = 12
MAX_BARS = 50
_SHARE_WORDS = re.compile(r"\b(share|split|breakdown|proportion|distribution|mix|"
                          r"percentage of|portion)\b", re.I)
_RATE_COLUMN = re.compile(r"pct|percent|rate|ratio|avg|average", re.I)

CHART_SYSTEM = (
    "Choose a chart for a query result. Options: bar, horizontal_bar, line, pie, scatter, or "
    "table when no chart helps. x must be a column name; y must be numeric column names."
)


class ChartChoice(BaseModel):
    type: ChartType
    x: str | None = None
    y: list[str] = Field(default_factory=list)


@dataclass(frozen=True)
class ChartDecision:
    type: ChartType
    x: str | None = None
    y: list[str] = field(default_factory=list)
    source: Literal["rule", "hint", "llm"] = "rule"


TABLE = ChartDecision("table")


class ChartDecider:
    def __init__(self, llm: LLM | None) -> None:
        self._llm = llm

    def decide(self, result: QueryResult, question: str,
               hint: ChartHint | None = None) -> ChartDecision:
        if hint is not None:
            return ChartDecision(hint.type, hint.x, list(hint.y), "hint")  # type: ignore[arg-type]
        decided = self._rules(result, question)
        if decided is not None:
            return decided
        return self._ask_llm(result, question)

    def _rules(self, result: QueryResult, question: str) -> ChartDecision | None:
        if result.row_count <= 1 or len(result.columns) < 2:
            return TABLE
        by_type: dict[str, list[str]] = {"number": [], "date": [], "text": [], "boolean": []}
        for column in result.columns:
            by_type[column.type].append(column.name)
        numbers, dates, texts = by_type["number"], by_type["date"], by_type["text"]
        if not numbers:
            return TABLE
        if dates and len(dates) == 1 and len(numbers) == len(result.columns) - 1:
            return ChartDecision("line", dates[0], numbers)
        if not texts and not dates and len(numbers) == 2:
            return ChartDecision("scatter", numbers[0], [numbers[1]])
        if len(texts) == 1 and len(numbers) == 1 and len(result.columns) == 2:
            return self._category_chart(result, question, texts[0], numbers[0])
        return None

    def _category_chart(self, result: QueryResult, question: str, x: str,
                        y: str) -> ChartDecision:
        values = [r[result.column_names.index(y)] for r in result.rows]
        if (result.row_count <= MAX_PIE_SLICES and _SHARE_WORDS.search(question)
                and not _RATE_COLUMN.search(y) and all(v is not None and v >= 0 for v in values)):
            return ChartDecision("pie", x, [y])
        if result.row_count > MAX_BARS:
            return TABLE
        kind: ChartType = "horizontal_bar" if result.row_count > MAX_VERTICAL_BARS else "bar"
        return ChartDecision(kind, x, [y])

    def _ask_llm(self, result: QueryResult, question: str) -> ChartDecision:
        if self._llm is None:
            return TABLE
        described = ", ".join(f"{c.name} ({c.type})" for c in result.columns)
        try:
            choice = self._llm.structured(
                Task.CHART, system=CHART_SYSTEM, schema=ChartChoice,
                user=f"Question: {question}\nColumns: {described}\nRows: {result.row_count}")
        except Exception:
            log.warning("Chart choice failed; showing a table", exc_info=True)
            return TABLE
        numeric = {c.name for c in result.columns if c.type == "number"}
        if choice.type == "table" or choice.x not in result.column_names or not choice.y \
                or not set(choice.y) <= numeric or _mostly_blank(result, choice.y):
            return TABLE
        return ChartDecision(choice.type, choice.x, choice.y, "llm")


MAX_BLANK_SHARE = 0.1


def _mostly_blank(result: QueryResult, columns: list[str]) -> bool:
    """Blank values would be drawn as zeros; don't chart a measure that is often missing."""
    for name in columns:
        index = result.column_names.index(name)
        blanks = sum(1 for row in result.rows if row[index] is None)
        if result.rows and blanks / len(result.rows) > MAX_BLANK_SHARE:
            return True
    return False
