"""Predefined, hand-written queries behind the role buttons."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from app.auth.roles import Role
from app.core.errors import Forbidden, NotFound

INR = "CASE WHEN p.currency = 'USD' THEN {amount} * CAST(:fx AS numeric) ELSE {amount} END"


def inr(amount: str) -> str:
    """SQL expression converting a PO amount to INR with the configured USD rate."""
    return INR.format(amount=amount)


@dataclass(frozen=True)
class CannedContext:
    today: date
    fx_usd_inr: float


@dataclass(frozen=True)
class ChartHint:
    type: str
    x: str
    y: tuple[str, ...]


@dataclass(frozen=True)
class CannedQuery:
    id: str
    label: str
    description: str
    roles: frozenset[Role]
    sql: str
    chart: ChartHint | None = None

    def params(self, ctx: CannedContext) -> dict[str, Any]:
        values: dict[str, Any] = {}
        if ":fx" in self.sql:
            values["fx"] = ctx.fx_usd_inr
        if ":today" in self.sql:
            values["today"] = ctx.today
        return values

    def literal_sql(self, ctx: CannedContext) -> str:
        """The query with its parameters written in, e.g. for validation or as an example."""
        return (self.sql.strip()
                .replace("CAST(:today AS date)", f"DATE '{ctx.today.isoformat()}'")
                .replace("CAST(:fx AS numeric)", f"{ctx.fx_usd_inr:g}"))

    def note(self, ctx: CannedContext) -> str:
        return f"USD orders are converted at ₹{ctx.fx_usd_inr:g} per USD." if ":fx" in self.sql \
            else ""


@dataclass
class Registry:
    _queries: dict[str, CannedQuery] = field(default_factory=dict)

    def register(self, queries: Iterable[CannedQuery]) -> None:
        for query in queries:
            if query.id in self._queries:
                raise ValueError(f"Duplicate button id {query.id}")
            self._queries[query.id] = query

    def ids(self) -> list[str]:
        return list(self._queries)

    def get(self, button_id: str) -> CannedQuery:
        try:
            return self._queries[button_id]
        except KeyError as exc:
            raise NotFound("That query button doesn't exist.") from exc

    def get_for(self, role: Role, button_id: str) -> CannedQuery:
        query = self.get(button_id)
        if role not in query.roles:
            raise Forbidden("That query button isn't available to your role.")
        return query

    def for_role(self, role: Role) -> list[CannedQuery]:
        return [q for q in self._queries.values() if role in q.roles]
