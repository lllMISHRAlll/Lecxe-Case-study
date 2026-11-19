from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.agents.service import ChatRequest
from app.api.deps import get_container, require
from app.api.sse import sse_stream
from app.auth.users import User
from app.container import Container
from app.rbac.capabilities import Capability

router = APIRouter(tags=["chat"])


@router.post("/chat/stream")
def chat_stream(
    body: ChatRequest,
    user: Annotated[User, Depends(require(Capability.CHAT_ASK))],
    container: Annotated[Container, Depends(get_container)],
) -> StreamingResponse:
    settings = container.settings
    container.limiter.hit("chat-minute", user.id, limit=settings.rate_limit_per_minute,
                          window_seconds=60)
    container.limiter.hit("chat-day", user.id, limit=settings.rate_limit_per_day,
                          window_seconds=86_400)
    service = container.chat_service
    turn = service.prepare(user, body)
    return StreamingResponse(sse_stream(service.run(turn)), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
