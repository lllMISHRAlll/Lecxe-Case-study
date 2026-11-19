"""Value hints and examples that make generated SQL use real spellings and good patterns."""

from __future__ import annotations

import re
from datetime import date

from rapidfuzz import fuzz

from app.auth.roles import Role
from app.po.catalog import Catalog
from app.sql.canned.base import CannedQuery, Registry

MAX_ITEMS = 5
MAX_EXAMPLES = 3
_WORD = re.compile(r"[a-z0-9]+")


def value_hints(question: str, catalog: Catalog) -> str:
    q = question.lower()
    items = sorted(
        ((fuzz.partial_ratio(i.name.lower(), q), i) for i in catalog.items if i.is_active),
        key=lambda pair: pair[0], reverse=True)
    matched = [f"{i.name} ({i.code}, unit {i.unit})" for score, i in items[:MAX_ITEMS]
               if score >= 85]
    lines = [
        "Vendor names: " + "; ".join(v.name for v in catalog.vendors if v.is_active),
        "Warehouse names: " + "; ".join(loc.name for loc in catalog.locations),
    ]
    if matched:
        lines.append("Items that may be meant: " + "; ".join(matched))
    return "\n".join(lines)


def _tokens(text: str) -> set[str]:
    return set(_WORD.findall(text.lower()))


def examples(question: str, role: Role, registry: Registry, today: date, fx: float) -> str:
    wanted = _tokens(question)

    def score(query: CannedQuery) -> int:
        return len(wanted & _tokens(f"{query.label} {query.description}"))

    picked = sorted(registry.for_role(role), key=score, reverse=True)[:MAX_EXAMPLES]
    blocks = []
    for query in picked:
        sql = query.sql.strip().replace("CAST(:today AS date)", f"DATE '{today.isoformat()}'")
        sql = sql.replace("CAST(:fx AS numeric)", f"{fx:g}")
        blocks.append(f"-- {query.label}: {query.description}\n{sql}")
    return "\n\n".join(blocks)


def strip_fences(sql: str) -> str:
    text = sql.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()
