"""Stream events emitted by graph nodes. The API turns them into Server-Sent Events."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from langgraph.config import get_stream_writer


@dataclass(frozen=True)
class StreamEvent:
    event: str
    data: dict[str, Any]


def emit(event: str, data: dict[str, Any]) -> None:
    get_stream_writer()(StreamEvent(event, data))


def step(node: str, label: str) -> None:
    emit("step", {"node": node, "label": label})


def stream_text(text: str) -> None:
    """Send fixed text as tokens, so replies stream like model output."""
    for token in re.findall(r"\S+\s*|\s+", text):
        emit("token", {"text": token})
