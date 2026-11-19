"""Runs one chat turn: checks the request, opens or creates the conversation, streams the graph."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.agents.deps import GraphDeps
from app.agents.events import StreamEvent
from app.agents.graph import build_graph
from app.auth.users import User
from app.history.repository import Conversation

log = logging.getLogger(__name__)

GENERIC_ERROR = "Something went wrong while answering. Please try again."
AI_UNAVAILABLE = ("The AI service isn't available right now (it rejected the request), so I "
                  "can't answer typed questions. The suggested questions still work.")
_AI_ERRORS = {"AuthenticationError", "OpenAIAuthenticationError", "PermissionDeniedError",
              "APIConnectionError", "APITimeoutError", "RateLimitError"}


def _ai_unavailable(exc: BaseException | None) -> bool:
    seen = 0
    while exc is not None and seen < 10:
        if type(exc).__name__ in _AI_ERRORS:
            return True
        exc, seen = exc.__cause__ or exc.__context__, seen + 1
    return False


class POAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["confirm", "cancel", "choose"]
    idempotency_key: str | None = None
    choice: str | None = Field(default=None, max_length=200)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversation_id: str | None = Field(default=None, max_length=64)
    message: str | None = Field(default=None, min_length=1, max_length=1000)
    button_id: str | None = Field(default=None, max_length=64)
    po_action: POAction | None = None

    @model_validator(mode="after")
    def exactly_one_input(self) -> ChatRequest:
        given = [x for x in (self.message, self.button_id, self.po_action) if x is not None]
        if len(given) != 1:
            raise ValueError("Send exactly one of message, button_id or po_action.")
        return self


@dataclass(frozen=True)
class PreparedTurn:
    user: User
    request: ChatRequest
    conversation: Conversation


class ChatService:
    def __init__(self, deps: GraphDeps) -> None:
        self.deps = deps
        self._graph = build_graph(deps)

    @property
    def tracing(self):
        return self.deps.tracing

    @classmethod
    def from_container(cls, container: Any) -> ChatService:
        return cls(container.graph_deps)

    # ------------------------------------------------------------------ steps

    def prepare(self, user: User, request: ChatRequest) -> PreparedTurn:
        """Checks that can fail with a normal HTTP error, before any streaming starts."""
        history = self.deps.history
        if request.button_id:
            self.deps.registry.get_for(user.role, request.button_id)
        if request.conversation_id:
            conversation = history.get_conversation(user.id, request.conversation_id)
        else:
            title = request.message or (self.deps.registry.get(request.button_id).label
                                        if request.button_id else "Purchase order")
            conversation = history.create_conversation(user.id, title)
        return PreparedTurn(user, request, conversation)

    def run(self, turn: PreparedTurn) -> Iterator[StreamEvent]:
        request, history = turn.request, self.deps.history
        conversation = turn.conversation
        yield StreamEvent("conversation", {"conversation_id": conversation.id,
                                           "title": conversation.title})
        recent = history.recent_turns(conversation.id)
        history.add_message(conversation.id, "user", self._user_text(request))
        state: dict[str, Any] = {
            "user": turn.user, "conversation_id": conversation.id, "message": request.message,
            "button_id": request.button_id,
            "po_action": request.po_action.model_dump() if request.po_action else None,
            "history": recent, "steps": [], "payload": {},
        }
        run_id = str(uuid.uuid4()) if self.tracing.enabled else None
        state["run_id"] = run_id
        config = self.tracing.run_config(turn.user, conversation.id, run_id)
        message_id = None
        try:
            for _namespace, event in self._graph.stream(state, config=config or None,
                                                        stream_mode="custom", subgraphs=True):
                if event.event == "saved":
                    message_id = event.data["message_id"]
                    continue
                yield event
        except GeneratorExit:
            raise
        except Exception as exc:
            reference = uuid.uuid4().hex[:8]
            log.exception("Chat turn failed, reference %s, LangSmith run id %s", reference,
                          run_id or "none (tracing off)")
            message = AI_UNAVAILABLE if _ai_unavailable(exc) else GENERIC_ERROR
            yield StreamEvent("error", {"message": message, "reference": reference})
        yield StreamEvent("done", {"message_id": message_id})

    def stream(self, user: User, request: ChatRequest) -> Iterator[StreamEvent]:
        yield from self.run(self.prepare(user, request))

    def _user_text(self, request: ChatRequest) -> str:
        if request.message:
            return request.message
        if request.button_id:
            return self.deps.registry.get(request.button_id).label
        assert request.po_action is not None
        return {"confirm": "Confirm PO", "cancel": "Cancel PO"}.get(
            request.po_action.type, "Chose an option")
