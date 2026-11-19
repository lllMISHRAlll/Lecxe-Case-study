"""Retries a structured LLM call once when the output doesn't parse."""

from __future__ import annotations

from collections.abc import Iterator

from pydantic import ValidationError

from app.llm.port import LLM, LLMOutputError, T
from app.llm.tasks import Task


class RetryingLLM:
    def __init__(self, inner: LLM) -> None:
        self._inner = inner

    def structured(self, task: Task, *, system: str, user: str, schema: type[T]) -> T:
        last: Exception | None = None
        for _ in range(2):
            try:
                return self._inner.structured(task, system=system, user=user, schema=schema)
            except (ValidationError, LLMOutputError, ValueError) as exc:
                last = exc
        raise LLMOutputError(f"{task} returned unusable output twice") from last

    def text(self, task: Task, *, system: str, user: str) -> str:
        return self._inner.text(task, system=system, user=user)

    def stream(self, task: Task, *, system: str, user: str) -> Iterator[str]:
        yield from self._inner.stream(task, system=system, user=user)
