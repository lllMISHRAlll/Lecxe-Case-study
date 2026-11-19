"""Anthropic (Claude) backend, using the official `anthropic` SDK.

* Fast tier (guardrails, routing, follow-ups, chart choice, PO extraction): Claude Haiku 5.5.
* Strong tier (schema linking, SQL, answers): Claude Sonnet 5.5.
* Thinking stays on (these models think adaptively by default); depth is set per task with
  `effort`. No sampling parameters: current models reject them.
* Strong-tier calls on models that support it use the server-side refusal fallback
  (`fallbacks: "default"`), so a policy decline is retried on a fallback model in the same call.
* When tracing is on, each call is wrapped by `trace(name, fn)` so it nests under the graph
  step that made it, uploaded through the masked LangSmith client.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

from app.llm.port import LLMOutputError, LLMRefusalError, T
from app.llm.tasks import Task, Tier

Tracer = Callable[[str, Callable[..., Any]], Callable[..., Any]]

STRUCTURED_MAX_TOKENS = 16_000
STREAM_MAX_TOKENS = 64_000
EFFORT: dict[Task, str] = {
    Task.SCHEMA_LINK: "high", Task.GENERATE_SQL: "high", Task.FIX_SQL: "high",
    Task.ANSWER: "medium",
}
FALLBACK_BETA = "server-side-fallback-2026-07-01"
# Models that accept server-side refusal fallbacks. Haiku has none.
_FALLBACK_MODEL_PREFIXES = ("claude-opus-5", "claude-sonnet-5-5", "claude-fable-5")


class AnthropicLLM:
    def __init__(self, *, fast_model: str, strong_model: str, api_key: str | None = None,
                 client: Any | None = None, trace: Tracer | None = None) -> None:
        if client is None:
            import anthropic

            client = anthropic.Anthropic(api_key=api_key, timeout=120.0, max_retries=2)
        self._client = client
        self.fast_model = fast_model
        self.strong_model = strong_model
        self.trace = trace

    # ------------------------------------------------------------------ request shape

    def _request(self, task: Task, system: str, user: str) -> dict[str, Any]:
        model = self.strong_model if task.tier is Tier.STRONG else self.fast_model
        request: dict[str, Any] = {
            "model": model,
            "system": system,
            "messages": [{"role": "user", "content": user}],
            "output_config": {"effort": EFFORT.get(task, "low")},
        }
        if model.startswith(_FALLBACK_MODEL_PREFIXES):
            request |= {"betas": [FALLBACK_BETA], "fallbacks": "default"}
        return request

    def _traced(self, task: Task, fn: Callable[..., Any]) -> Callable[..., Any]:
        return self.trace(f"llm.{task}", fn) if self.trace else fn

    @staticmethod
    def _check(stop_reason: str | None, task: Task) -> None:
        if stop_reason == "refusal":
            raise LLMRefusalError(f"The model declined the {task} request")

    # ------------------------------------------------------------------ LLM port

    def structured(self, task: Task, *, system: str, user: str, schema: type[T]) -> T:
        def call(**request: Any) -> Any:
            return self._client.beta.messages.parse(max_tokens=STRUCTURED_MAX_TOKENS,
                                                    output_format=schema, **request)

        response = self._traced(task, call)(**self._request(task, system, user))
        self._check(response.stop_reason, task)
        parsed = response.parsed_output
        if parsed is None:
            raise LLMOutputError(f"{task} returned no structured output")
        return parsed if isinstance(parsed, schema) else schema.model_validate(parsed)

    def text(self, task: Task, *, system: str, user: str) -> str:
        def call(**request: Any) -> Any:
            return self._client.beta.messages.create(max_tokens=STRUCTURED_MAX_TOKENS,
                                                     **request)

        response = self._traced(task, call)(**self._request(task, system, user))
        self._check(response.stop_reason, task)
        return "".join(b.text for b in response.content if b.type == "text")

    def stream(self, task: Task, *, system: str, user: str) -> Iterator[str]:
        def call(**request: Any) -> Iterator[str]:
            with self._client.beta.messages.stream(max_tokens=STREAM_MAX_TOKENS,
                                                   **request) as stream:
                yield from stream.text_stream
                self._check(stream.get_final_message().stop_reason, task)

        yield from self._traced(task, call)(**self._request(task, system, user))
