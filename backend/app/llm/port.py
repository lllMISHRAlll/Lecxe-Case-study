"""The interface every LLM backend implements. Nodes depend on this, never on a vendor SDK."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol, TypeVar

from pydantic import BaseModel

from app.llm.tasks import Task

T = TypeVar("T", bound=BaseModel)


class LLMOutputError(RuntimeError):
    """The model returned output that could not be parsed, even after a retry."""


class LLM(Protocol):
    def structured(self, task: Task, *, system: str, user: str, schema: type[T]) -> T: ...

    def text(self, task: Task, *, system: str, user: str) -> str: ...

    def stream(self, task: Task, *, system: str, user: str) -> Iterator[str]: ...
