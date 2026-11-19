"""Matches what the user typed to real vendors, items and locations (active only)."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field

from rapidfuzz import fuzz, process

from app.po.catalog import Catalog
from app.po.models import ItemRef, LocationRef, VendorRef

MATCH_SCORE = 85
CHOICE_SCORE = 70
CLEAR_LEAD = 8
MAX_CHOICES = 5


@dataclass
class Resolution[T]:
    match: T | None = None
    choices: list[T] = field(default_factory=list)


def _norm(text: str) -> str:
    text = text.lower().replace("×", "x").replace("–", " ").replace("-", " ")
    text = re.sub(r"(?<=\d)x(?=\d)", " ", text)  # 25x40x2mm -> 25 40 2mm
    return re.sub(r"[^\w.%+]+", " ", text).strip()


def _resolve[T](query: str, candidates: list[T], name: Callable[[T], str],
             exact: Callable[[T], list[str]]) -> Resolution[T]:
    wanted = _norm(query)
    for candidate in candidates:
        if wanted in (_norm(e) for e in exact(candidate)):
            return Resolution(match=candidate)
    if not wanted or not candidates:
        return Resolution()
    names = [_norm(name(c)) for c in candidates]
    scored = process.extract(wanted, names, scorer=fuzz.token_set_ratio, limit=MAX_CHOICES)
    if not scored or scored[0][1] < CHOICE_SCORE:
        return Resolution()
    best = scored[0][1]
    close = [candidates[i] for _, score, i in scored
             if score >= CHOICE_SCORE and best - score < CLEAR_LEAD]
    if best >= MATCH_SCORE and len(close) == 1:
        return Resolution(match=close[0])
    return Resolution(choices=close)


class EntityResolver:
    def __init__(self, catalog: Catalog) -> None:
        self.catalog = catalog

    def vendor(self, query: str) -> Resolution[VendorRef]:
        active = [v for v in self.catalog.vendors if v.is_active]
        return _resolve(query, active, lambda v: v.name, lambda v: [v.name])

    def item(self, query: str) -> Resolution[ItemRef]:
        active = [i for i in self.catalog.items if i.is_active]
        return _resolve(query, active, lambda i: i.name, lambda i: [i.code, i.name])

    def location(self, query: str) -> Resolution[LocationRef]:
        return _resolve(query, self.catalog.locations, lambda loc: loc.name,
                        lambda loc: [loc.name])
