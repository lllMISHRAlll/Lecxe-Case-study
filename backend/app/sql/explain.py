"""Dry-runs a query with EXPLAIN on the database: catches unknown columns and costly plans
without executing anything."""

from __future__ import annotations

import json

from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError

from app.sql.validator import SqlRejectedError


class SqlExplainer:
    def __init__(self, engine: Engine, *, cost_limit: float) -> None:
        self._engine = engine
        self._cost_limit = cost_limit

    def check(self, sql: str) -> float:
        try:
            with self._engine.connect() as conn:
                plan = conn.execute(text(f"EXPLAIN (FORMAT JSON) {sql}")).scalar()
        except DBAPIError as exc:
            raise SqlRejectedError("explain", _db_message(exc)) from exc
        data = json.loads(plan) if isinstance(plan, str) else plan
        cost = float(data[0]["Plan"]["Total Cost"])
        if cost > self._cost_limit:
            raise SqlRejectedError(
                "explain", f"The query is too expensive (cost {cost:,.0f}). Narrow it with "
                           "filters, fewer joins or aggregation.")
        return cost


def _db_message(exc: DBAPIError) -> str:
    """First line of the database error, e.g. 'column "nme" does not exist'."""
    original = getattr(exc, "orig", None)
    diag = getattr(original, "diag", None)
    primary = getattr(diag, "message_primary", None)
    return primary or str(original or exc).splitlines()[0]
