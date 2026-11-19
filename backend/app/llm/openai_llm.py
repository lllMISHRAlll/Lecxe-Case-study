"""OpenAI backend through LangChain, so LangSmith traces every call automatically."""

from __future__ import annotations

from collections.abc import Iterator

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.llm.port import T
from app.llm.tasks import Task, Tier


class OpenAILLM:
    def __init__(self, *, api_key: str, fast_model: str, strong_model: str) -> None:
        common = {"api_key": api_key, "temperature": 0, "timeout": 60, "max_retries": 2}
        self._models = {Tier.FAST: ChatOpenAI(model=fast_model, **common),
                        Tier.STRONG: ChatOpenAI(model=strong_model, **common)}

    def _model(self, task: Task) -> ChatOpenAI:
        return self._models[task.tier]

    @staticmethod
    def _messages(system: str, user: str):
        return [SystemMessage(system), HumanMessage(user)]

    def structured(self, task: Task, *, system: str, user: str, schema: type[T]) -> T:
        runnable = self._model(task).with_structured_output(schema, method="function_calling")
        result = runnable.invoke(self._messages(system, user),
                                 config={"run_name": f"llm.{task}", "tags": [str(task)]})
        return result if isinstance(result, schema) else schema.model_validate(result)

    def text(self, task: Task, *, system: str, user: str) -> str:
        reply = self._model(task).invoke(self._messages(system, user),
                                         config={"run_name": f"llm.{task}", "tags": [str(task)]})
        return str(reply.content)

    def stream(self, task: Task, *, system: str, user: str) -> Iterator[str]:
        for chunk in self._model(task).stream(
                self._messages(system, user),
                config={"run_name": f"llm.{task}", "tags": [str(task)]}):
            if chunk.content:
                yield str(chunk.content)
