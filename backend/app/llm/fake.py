"""A scripted LLM for tests: returns prepared responses per task and records every prompt."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

from app.llm.port import T
from app.llm.tasks import Task

Response = Any  # a string, a dict, a model instance, or a callable(system, user) -> one of those
Script = dict[Task, list[Response] | Callable[[str, str], Response]]


class ScriptExhaustedError(AssertionError):
    """A test asked the fake LLM for a task it had no scripted response for."""


@dataclass(frozen=True)
class Call:
    task: Task
    system: str
    user: str


@dataclass
class ScriptedLLM:
    script: Script = field(default_factory=dict)
    calls: list[Call] = field(default_factory=list)

    def _next(self, task: Task, system: str, user: str) -> Response:
        self.calls.append(Call(task, system, user))
        entry = self.script.get(task)
        if callable(entry):
            return entry(system, user)
        if not entry:
            raise ScriptExhaustedError(f"No scripted response left for task {task!s}")
        return entry.pop(0)

    def structured(self, task: Task, *, system: str, user: str, schema: type[T]) -> T:
        response = self._next(task, system, user)
        if isinstance(response, schema):
            return response
        if isinstance(response, BaseModel):
            return schema.model_validate(response.model_dump())
        return schema.model_validate(response)

    def text(self, task: Task, *, system: str, user: str) -> str:
        return str(self._next(task, system, user))

    def stream(self, task: Task, *, system: str, user: str) -> Iterator[str]:
        yield from re.findall(r"\S+\s*|\s+", self.text(task, system=system, user=user))

    def calls_for(self, task: Task) -> list[Call]:
        return [c for c in self.calls if c.task is task]
