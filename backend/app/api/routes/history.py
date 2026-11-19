from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel

from app.api.deps import get_container, require
from app.auth.users import User
from app.container import Container
from app.core.jsonable import to_jsonable
from app.po.rules import apply_defaults, review
from app.rbac.capabilities import Capability

router = APIRouter(tags=["history"])
HistoryUser = Annotated[User, Depends(require(Capability.HISTORY_OWN))]
ContainerDep = Annotated[Container, Depends(get_container)]


class ConversationOut(BaseModel):
    id: str
    title: str
    updated_at: datetime


class MessageOut(BaseModel):
    id: str
    sender: str
    text: str
    payload: dict[str, Any]
    created_at: datetime | None


class ConversationDetail(BaseModel):
    id: str
    title: str
    messages: list[MessageOut]
    open_po_draft: dict[str, Any] | None


@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(user: HistoryUser, container: ContainerDep) -> list[ConversationOut]:
    return [ConversationOut(id=c.id, title=c.title, updated_at=c.updated_at)
            for c in container.history.list_conversations(user.id)]


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: str, user: HistoryUser,
                     container: ContainerDep) -> ConversationDetail:
    history = container.history
    conversation = history.get_conversation(user.id, conversation_id)
    messages = history.messages(user.id, conversation_id)
    draft = history.open_draft(conversation_id)
    contract = None
    if draft is not None:
        draft = apply_defaults(draft, container.clock.today())
        contract = to_jsonable(draft.to_contract(review(draft)))
    return ConversationDetail(
        id=conversation.id, title=conversation.title, open_po_draft=contract,
        messages=[MessageOut(id=m.id, sender=m.sender, text=m.text, payload=m.payload,
                             created_at=m.created_at) for m in messages])


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: str, user: HistoryUser,
                        container: ContainerDep) -> Response:
    container.history.delete_conversation(user.id, conversation_id)
    return Response(status_code=204)
