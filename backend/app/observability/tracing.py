"""LangSmith tracing with masking.

* One trace per chat turn ("chat_turn"); every graph node is a child run, so guardrails,
  validation, execution and the PO insert are visible, not only LLM calls.
* Every input and output goes through `scrub` before upload: result rows are removed,
  personal data is masked, users become a role and a hashed id.
* The conversation id is the thread id, so a whole chat groups together.
* Off unless LANGSMITH_TRACING is true and an API key is set.
"""

from __future__ import annotations

import hashlib
import os
import re
import uuid
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel

from app.agents.prompts import PROMPT_VERSION
from app.auth.users import DEMO_USERS, User
from app.core.config import Settings
from app.guardrails.masker import Masker
from app.sql.executor import QueryResult
from app.viz.reducer import Reduced

ROW_KEYS = frozenset({"rows", "top_rows", "records", "data", "reduced"})
_ROWS_BLOCK = re.compile(r"Top \d+ rows[^\n]*:\n(?:- [^\n]*(?:\n|$))*")
_masker = Masker()


def hash_user(user_id: str) -> str:
    return hashlib.sha256(user_id.encode()).hexdigest()[:12]


_USER_NAMES = re.compile("|".join(re.escape(u.name) for u in DEMO_USERS))


def _clean_text(text: str) -> str:
    text = _USER_NAMES.sub("[USER]", _ROWS_BLOCK.sub("[rows removed]\n", text))
    return _masker.mask(text)


def _user(value: Any) -> Any:
    if isinstance(value, User):
        return {"role": value.role.value, "user_hash": hash_user(value.id)}
    return "[user removed]"


def _removed(value: Any) -> str:
    return f"[{len(value)} rows removed]" if isinstance(value, list) else "[removed]"


def scrub(value: Any) -> Any:
    """Make a trace payload safe to upload. Used as LangSmith's hide_inputs/hide_outputs."""
    if isinstance(value, QueryResult):
        return {"columns": value.column_names, "row_count": value.row_count,
                "truncated": value.truncated}
    if isinstance(value, Reduced):
        return {"row_count": value.row_count, "columns": [c for c, _ in value.columns]}
    if isinstance(value, User):
        return _user(value)
    if isinstance(value, BaseModel):
        return scrub(value.model_dump(mode="json"))
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if key in ROW_KEYS:
                out[key] = _removed(item)
            elif key == "user":
                out[key] = _user(item)
            elif key == "result" and not isinstance(item, QueryResult):
                out[key] = "[removed]"
            else:
                out[key] = scrub(item)
        return out
    if isinstance(value, list | tuple):
        return [scrub(v) for v in value]
    if isinstance(value, str):
        return _clean_text(value)
    return value


class Tracing:
    def __init__(self, settings: Settings, client: Any | None = None) -> None:
        self.settings = settings
        self.enabled = settings.tracing_enabled
        self._client = client
        self.tracer_factory: Callable[[dict[str, Any]], Any] | None = None
        # Only our masked tracer may send data; switch off LangChain's env-based auto tracing.
        os.environ["LANGSMITH_TRACING"] = "false"
        os.environ["LANGCHAIN_TRACING_V2"] = "false"

    @property
    def client(self) -> Any:
        if self._client is None:
            from langsmith import Client

            self._client = Client(
                api_key=self.settings.langsmith_api_key.get_secret_value(),
                api_url=self.settings.langsmith_endpoint or None,
                hide_inputs=scrub, hide_outputs=scrub)
        return self._client

    def run_config(self, user: User, conversation_id: str, run_id: str | None) -> dict[str, Any]:
        if not self.enabled or run_id is None:
            return {}
        metadata = {"role": user.role.value, "user_hash": hash_user(user.id),
                    "thread_id": conversation_id, "session_id": conversation_id,
                    "env": self.settings.app_env, "prompt_version": PROMPT_VERSION}
        tags = [f"role:{user.role.value}", f"env:{self.settings.app_env}"]
        if self.tracer_factory is not None:
            tracer = self.tracer_factory(metadata)
        else:
            from app.observability.trace_shape import ShapedTracer

            tracer = ShapedTracer(project_name=self.settings.langsmith_project,
                                     client=self.client)
        return {"callbacks": [tracer], "run_id": uuid.UUID(run_id), "run_name": "chat_turn",
                "tags": tags, "metadata": metadata}

    def feedback(self, run_id: str | None, score: int) -> None:
        if self.enabled and run_id:
            self.client.create_feedback(run_id, key="user_score", score=score)
