"""Builds the chart spec from the real rows. The LLM never writes chart data."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.sql.executor import QueryResult
from app.viz.chart_rules import ChartDecision


def _chart_value(value: Any) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, Decimal | int | float):
        return float(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def build_chart(result: QueryResult, decision: ChartDecision, *, title: str) -> dict[str, Any]:
    if decision.type == "table" or decision.x is None:
        return {"type": "table", "title": title, "x": None, "y": [], "data": []}
    keep = [decision.x, *decision.y]
    data = [{k: _chart_value(record[k]) for k in keep} for record in result.records()]
    return {"type": decision.type, "title": title, "x": decision.x, "y": list(decision.y),
            "data": data}
