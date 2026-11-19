from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import require
from app.auth.users import User
from app.rbac.capabilities import Capability
from app.sql.canned import REGISTRY

router = APIRouter(tags=["canned"])


class ButtonOut(BaseModel):
    id: str
    label: str
    description: str


@router.get("/canned", response_model=list[ButtonOut])
def list_buttons(
    user: Annotated[User, Depends(require(Capability.CANNED_RUN))],
) -> list[ButtonOut]:
    return [ButtonOut(id=q.id, label=q.label, description=q.description)
            for q in REGISTRY.for_role(user.role)]
