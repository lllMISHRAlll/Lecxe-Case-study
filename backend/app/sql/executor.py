"""Runs a read-only query and returns rows capped at the row limit."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError, OperationalError

ColumnType = Literal["number", "date", "boolean", "text"]


class QueryFailedError(RuntimeError):
    pass


@dataclass(frozen=True)
class Column:
    name: str
    type: ColumnType


@dataclass(frozen=True)
class QueryResult:
    columns: list[Column]
    rows: list[list[Any]]
    truncated: bool

    @property
    def row_count(self) -> int:
        return len(self.rows)

    @property
    def column_names(self) -> list[str]:
        return [c.name for c in self.columns]

    def records(self) -> list[dict[str, Any]]:
        return [dict(zip(self.column_names, row, strict=True)) for row in self.rows]


class QueryExecutor:
    def __init__(self, engine: Engine, *, row_cap: int) -> None:
        self._engine = engine
        self._row_cap = row_cap

    def run(self, sql: str, params: dict[str, Any] | None = None) -> QueryResult:
        try:
            with self._engine.connect() as conn:
                result = conn.execute(text(sql), params or {})
                names = list(result.keys())
                fetched = [list(r) for r in result.fetchmany(self._row_cap + 1)]
        except OperationalError as exc:
            raise QueryFailedError(_message(exc)) from exc
        except DBAPIError as exc:
            raise QueryFailedError(_message(exc)) from exc
        truncated = len(fetched) > self._row_cap
        rows = fetched[: self._row_cap]
        columns = [Column(name, _infer_type([r[i] for r in rows])) for i, name in
                   enumerate(names)]
        return QueryResult(columns=columns, rows=rows, truncated=truncated)


def _infer_type(values: list[Any]) -> ColumnType:
    sample = next((v for v in values if v is not None), None)
    if isinstance(sample, bool):
        return "boolean"
    if isinstance(sample, int | float | Decimal):
        return "number"
    if isinstance(sample, datetime | date):
        return "date"
    return "text"


def _message(exc: DBAPIError) -> str:
    original = getattr(exc, "orig", None)
    sqlstate = getattr(original, "sqlstate", None)
    if sqlstate == "57014":  # query_canceled (statement timeout)
        return "The query took too long and was stopped."
    diag = getattr(original, "diag", None)
    return getattr(diag, "message_primary", None) or str(original or exc).splitlines()[0]
