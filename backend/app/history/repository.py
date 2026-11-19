"""Chat history and PO drafts, stored in the assistant schema.

Every read is scoped to the signed-in user; other users' conversations look like 404s.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

from sqlalchemy import Engine, text

from app.agents.routing.rewriter import Turn
from app.core.clock import Clock
from app.core.errors import NotFound
from app.core.jsonable import to_jsonable
from app.po.models import PODraft

TITLE_LIMIT = 61


class DraftStatusError(RuntimeError):
    pass


@dataclass(frozen=True)
class Conversation:
    id: str
    title: str
    updated_at: datetime


@dataclass(frozen=True)
class Message:
    id: str
    sender: Literal["user", "assistant"]
    text: str
    payload: dict[str, Any] = field(default_factory=dict)
    langsmith_run_id: str | None = None
    created_at: datetime | None = None


def make_title(question: str) -> str:
    question = " ".join(question.split())
    if len(question) <= TITLE_LIMIT:
        return question
    words, title = question.split(" "), ""
    for word in words:
        candidate = f"{title} {word}".strip()
        if len(candidate) > TITLE_LIMIT:
            break
        title = candidate
    return title + "…"


class HistoryRepository:
    def __init__(self, engine: Engine, *, clock: Clock) -> None:
        self._engine = engine
        self._clock = clock

    # ------------------------------------------------------------------ conversations

    def create_conversation(self, user_id: str, first_question: str) -> Conversation:
        conv = Conversation(str(uuid.uuid4()), make_title(first_question), self._clock.now())
        with self._engine.begin() as conn:
            conn.execute(text(
                "INSERT INTO assistant.conversations (id, user_id, title, created_at, "
                "updated_at) VALUES (:id, :user_id, :title, :now, :now)"),
                {"id": conv.id, "user_id": user_id, "title": conv.title,
                 "now": conv.updated_at})
        return conv

    def get_conversation(self, user_id: str, conversation_id: str) -> Conversation:
        with self._engine.connect() as conn:
            row = conn.execute(text(
                "SELECT id, title, updated_at FROM assistant.conversations "
                "WHERE id = :id AND user_id = :user_id AND NOT is_deleted"),
                {"id": conversation_id, "user_id": user_id}).first()
        if row is None:
            raise NotFound("Conversation not found.")
        return Conversation(row.id, row.title, row.updated_at)

    def list_conversations(self, user_id: str) -> list[Conversation]:
        with self._engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT id, title, updated_at FROM assistant.conversations "
                "WHERE user_id = :user_id AND NOT is_deleted ORDER BY updated_at DESC, id"),
                {"user_id": user_id}).all()
        return [Conversation(r.id, r.title, r.updated_at) for r in rows]

    def delete_conversation(self, user_id: str, conversation_id: str) -> None:
        self.get_conversation(user_id, conversation_id)
        with self._engine.begin() as conn:
            conn.execute(text("UPDATE assistant.conversations SET is_deleted = true "
                              "WHERE id = :id"), {"id": conversation_id})

    # ------------------------------------------------------------------ messages

    def add_message(self, conversation_id: str, sender: str, text_: str,
                    payload: dict[str, Any] | None = None, run_id: str | None = None) -> str:
        message_id = str(uuid.uuid4())
        now = self._clock.now()
        with self._engine.begin() as conn:
            conn.execute(text(
                "INSERT INTO assistant.messages (id, conversation_id, sender, text, payload, "
                "langsmith_run_id, created_at) VALUES (:id, :conv, :sender, :text, "
                "CAST(:payload AS jsonb), :run_id, :now)"),
                {"id": message_id, "conv": conversation_id, "sender": sender, "text": text_,
                 "payload": json.dumps(to_jsonable(payload or {})), "run_id": run_id,
                 "now": now})
            conn.execute(text("UPDATE assistant.conversations SET updated_at = :now "
                              "WHERE id = :id"), {"now": now, "id": conversation_id})
        return message_id

    def messages(self, user_id: str, conversation_id: str) -> list[Message]:
        self.get_conversation(user_id, conversation_id)
        with self._engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT id, sender, text, payload, langsmith_run_id, created_at "
                "FROM assistant.messages WHERE conversation_id = :conv "
                "ORDER BY seq"), {"conv": conversation_id}).all()
        return [Message(r.id, r.sender, r.text, r.payload, r.langsmith_run_id, r.created_at)
                for r in rows]

    def recent_turns(self, conversation_id: str, limit: int = 3) -> list[Turn]:
        with self._engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT sender, text FROM assistant.messages WHERE conversation_id = :conv "
                "ORDER BY seq"), {"conv": conversation_id}).all()
        turns: list[Turn] = []
        question: str | None = None
        for row in rows:
            if row.sender == "user":
                question = row.text
            elif question is not None:
                turns.append(Turn(question, row.text))
                question = None
        return turns[-limit:]

    def set_feedback(self, user_id: str, message_id: str, score: int) -> str | None:
        with self._engine.begin() as conn:
            row = conn.execute(text(
                "UPDATE assistant.messages m SET feedback = :score "
                "FROM assistant.conversations c WHERE m.id = :id AND c.id = m.conversation_id "
                "AND c.user_id = :user_id AND NOT c.is_deleted RETURNING m.langsmith_run_id"),
                {"score": score, "id": message_id, "user_id": user_id}).first()
        if row is None:
            raise NotFound("Message not found.")
        return row.langsmith_run_id

    # ------------------------------------------------------------------ PO drafts

    def open_draft(self, conversation_id: str) -> PODraft | None:
        with self._engine.connect() as conn:
            row = conn.execute(text(
                "SELECT draft FROM assistant.po_drafts WHERE conversation_id = :conv "
                "AND status = 'open'"), {"conv": conversation_id}).first()
        return PODraft.model_validate(row.draft) if row else None

    def save_draft(self, conversation_id: str, draft: PODraft) -> None:
        body = json.dumps(draft.model_dump(mode="json"))
        now = self._clock.now()
        with self._engine.begin() as conn:
            updated = conn.execute(text(
                "UPDATE assistant.po_drafts SET draft = CAST(:draft AS jsonb), "
                "idempotency_key = :key, updated_at = :now "
                "WHERE conversation_id = :conv AND status = 'open'"),
                {"draft": body, "key": draft.idempotency_key, "now": now,
                 "conv": conversation_id}).rowcount
            if not updated:
                conn.execute(text(
                    "INSERT INTO assistant.po_drafts (id, conversation_id, draft, status, "
                    "idempotency_key, updated_at) VALUES (:id, :conv, CAST(:draft AS jsonb), "
                    "'open', :key, :now)"),
                    {"id": str(uuid.uuid4()), "conv": conversation_id, "draft": body,
                     "key": draft.idempotency_key, "now": now})

    def close_draft(self, conversation_id: str, status: Literal["confirmed", "cancelled"],
                    created_po_id: str | None = None) -> None:
        with self._engine.begin() as conn:
            changed = conn.execute(text(
                "UPDATE assistant.po_drafts SET status = :status, created_po_id = :po_id, "
                "updated_at = :now WHERE conversation_id = :conv AND status = 'open'"),
                {"status": status, "po_id": created_po_id, "now": self._clock.now(),
                 "conv": conversation_id}).rowcount
        if not changed:
            raise DraftStatusError("There is no open PO draft in this conversation.")
