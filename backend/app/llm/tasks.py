"""Every LLM call names its task. The task decides which model tier serves it."""

from __future__ import annotations

from enum import StrEnum


class Tier(StrEnum):
    FAST = "fast"
    STRONG = "strong"


class Task(StrEnum):
    GUARD = "guard"
    REWRITE = "rewrite"
    ROUTE = "route"
    SCHEMA_LINK = "schema_link"
    GENERATE_SQL = "generate_sql"
    FIX_SQL = "fix_sql"
    CHART = "chart"
    ANSWER = "answer"
    CHAT_REPLY = "chat_reply"
    PO_EXTRACT = "po_extract"

    @property
    def tier(self) -> Tier:
        return Tier.STRONG if self in _STRONG else Tier.FAST


_STRONG = {Task.SCHEMA_LINK, Task.GENERATE_SQL, Task.FIX_SQL, Task.ANSWER}
