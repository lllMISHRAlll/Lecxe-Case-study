from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, ConfigDict

from app.api.deps import get_container, require
from app.auth.users import User
from app.container import Container
from app.rbac.capabilities import Capability

router = APIRouter(tags=["feedback"])


class FeedbackIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message_id: str
    score: Literal[1, -1]


@router.post("/feedback", status_code=204)
def send_feedback(body: FeedbackIn,
                  user: Annotated[User, Depends(require(Capability.FEEDBACK_SEND))],
                  container: Annotated[Container, Depends(get_container)]) -> Response:
    run_id = container.history.set_feedback(user.id, body.message_id, body.score)
    container.feedback_sink(run_id, body.score)
    return Response(status_code=204)
