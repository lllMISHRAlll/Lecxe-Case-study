"""The state that flows through the graph. One run per user message or button click."""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

from app.agents.routing.rewriter import Turn
from app.auth.users import User
from app.po.models import PODraft
from app.sql.executor import QueryResult
from app.viz.reducer import Reduced


def merge(left: dict[str, Any] | None, right: dict[str, Any] | None) -> dict[str, Any]:
    return {**(left or {}), **(right or {})}


class AgentState(TypedDict, total=False):
    # request
    user: User
    conversation_id: str
    message: str | None
    button_id: str | None
    po_action: dict[str, Any] | None
    history: list[Turn]
    # understanding
    question: str
    intent: str
    po_command: str | None
    # SQL
    linked_tables: list[str]
    sql: str | None
    sql_params: dict[str, Any]
    sql_source: str
    sql_errors: list[str]
    sql_valid: bool
    attempts: int
    gave_up: bool
    chart_hint: Any
    notes: list[str]
    # results
    result: QueryResult | None
    reduced: Reduced | None
    answer: str
    reply: str | None
    reply_mode: str | None  # "text" (stream reply as is) or "chat" (LLM small talk)
    # PO
    po_draft: PODraft | None
    po_unresolved: list[Any]
    po_notes: list[str]
    # bookkeeping
    payload: Annotated[dict[str, Any], merge]
    steps: Annotated[list[str], operator.add]
