"""What each role may do. Data access per table lives in `scope.py`."""

from __future__ import annotations

from enum import StrEnum

from app.auth.roles import Role


class Capability(StrEnum):
    CHAT_ASK = "chat.ask"
    CANNED_RUN = "canned.run"
    PO_CREATE = "po.create"
    HISTORY_OWN = "history.own"
    FEEDBACK_SEND = "feedback.send"


_EVERYONE = {Capability.CHAT_ASK, Capability.CANNED_RUN, Capability.HISTORY_OWN,
             Capability.FEEDBACK_SEND}

ROLE_CAPABILITIES: dict[Role, frozenset[Capability]] = {
    Role.PROCUREMENT_MANAGER: frozenset(_EVERYONE | {Capability.PO_CREATE}),
    Role.BUSINESS_OWNER: frozenset(_EVERYONE),
    Role.WAREHOUSE_MANAGER: frozenset(_EVERYONE),
}


def has_capability(role: Role, capability: Capability) -> bool:
    return capability in ROLE_CAPABILITIES[role]
