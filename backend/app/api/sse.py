"""Server-Sent Events: wire format and the schema of every event (see docs/API_CONTRACT.md)."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from app.agents.events import StreamEvent
from app.core.jsonable import to_jsonable


class _Event(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ConversationEvent(_Event):
    conversation_id: str
    title: str


class StepEvent(_Event):
    node: str
    label: str
    status: Literal["done", "warn", "error"] = "done"


class SqlEvent(_Event):
    sql: str
    source: Literal["button", "generated", "fixed"]
    attempt: int


class ColumnOut(_Event):
    name: str
    type: Literal["number", "date", "boolean", "text"]


class RowsEvent(_Event):
    columns: list[ColumnOut]
    rows: list[list[Any]]
    row_count: int
    truncated: bool


class ChartEvent(_Event):
    type: Literal["bar", "horizontal_bar", "line", "pie", "scatter", "table"]
    title: str
    x: str | None
    y: list[str]
    data: list[dict[str, Any]]


class TextEvent(_Event):
    text: str


class Option(_Event):
    id: str
    label: str


class ChoicesEvent(_Event):
    prompt: str
    options: list[Option]


class PODraftEvent(_Event):
    draft: dict[str, Any]


class POCreatedEvent(_Event):
    po_number: str
    po_id: str
    total_amount: str
    currency: str


class ErrorEvent(_Event):
    message: str
    reference: str


class DoneEvent(_Event):
    message_id: str | None


EVENT_MODELS: dict[str, type[BaseModel]] = {
    "conversation": ConversationEvent, "step": StepEvent, "sql": SqlEvent, "rows": RowsEvent,
    "chart": ChartEvent, "token": TextEvent, "answer_replace": TextEvent,
    "choices": ChoicesEvent, "po_draft": PODraftEvent, "po_created": POCreatedEvent,
    "error": ErrorEvent, "done": DoneEvent,
}


def format_event(event: StreamEvent) -> str:
    data = json.dumps(to_jsonable(event.data), ensure_ascii=False)
    return f"event: {event.event}\ndata: {data}\n\n"


def sse_stream(events: Iterator[StreamEvent]) -> Iterator[str]:
    for event in events:
        yield format_event(event)
