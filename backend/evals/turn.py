"""Pure helpers for the DeepEval suite: read a chat turn's events, render rows as text, load the
per-role golden files and average scores. No model and no database, so unit tested."""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.agents.events import StreamEvent

DATASETS = Path(__file__).parent / "datasets"
ROLES = ("business_owner", "procurement_manager", "warehouse_manager")


@dataclass
class Turn:
    answer: str = ""
    sql: list[str] = field(default_factory=list)
    columns: list[str] | None = None
    rows: list[list[Any]] | None = None
    steps: list[str] = field(default_factory=list)
    error: str | None = None


def collect_turn(events: Iterable[StreamEvent]) -> Turn:
    turn, tokens = Turn(), []
    for e in events:
        if e.event == "token":
            tokens.append(e.data["text"])
        elif e.event == "answer_replace":
            tokens = [e.data["text"]]
        elif e.event == "sql":
            turn.sql.append(e.data["sql"])
        elif e.event == "rows":
            turn.columns = [c["name"] for c in e.data["columns"]]
            turn.rows = e.data["rows"]
        elif e.event == "step":
            turn.steps.append(e.data["node"])
        elif e.event == "error":
            turn.error = e.data["message"]
    turn.answer = "".join(tokens).strip()
    return turn


def _cell(value: Any) -> str:
    if hasattr(value, "isoformat"):
        return value.isoformat()[:10]
    if hasattr(value, "as_tuple") or isinstance(value, float):
        return f"{round(float(value), 2):g}"
    return str(value)


def render_rows(columns: list[str], rows: list[list[Any]], limit: int = 25) -> str:
    if not rows:
        return "No rows returned."
    lines = [" | ".join(columns), *(" | ".join(_cell(v) for v in r) for r in rows[:limit])]
    if len(rows) > limit:
        lines.append(f"... and {len(rows) - limit} more rows")
    return "\n".join(lines)


def load_role_cases(role: str) -> list[dict[str, Any]]:
    return json.loads((DATASETS / f"golden_{role}.json").read_text())


def summarise(results: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    """Per role: case count and the mean of each metric over the cases that have it."""
    buckets: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    counts: dict[str, int] = defaultdict(int)
    for r in results:
        counts[r["role"]] += 1
        for metric, score in r["scores"].items():
            buckets[r["role"]][metric].append(score)
    return {role: {"cases": counts[role],
                   **{m: sum(v) / len(v) for m, v in buckets[role].items()}}
            for role in counts}
