"""Decides where a message goes. Rules first; the LLM classifier only for the rest."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

from app.llm.port import LLM, LLMOutputError
from app.llm.tasks import Task

log = logging.getLogger(__name__)

MIN_CONFIDENCE = 0.6
LEAVE_DRAFT_CONFIDENCE = 0.8

_PO_REQUEST = re.compile(
    r"\b(raise|create|make|place|draft|new|open|prepare|issue)\b.{0,25}"
    r"\b(po|p\.o\.?|purchase order)\b", re.I)
_SMALL_TALK = re.compile(
    r"^\s*(hi|hello|hey|thanks|thank you|thx|ok|okay|help|good (morning|afternoon|evening)|"
    r"what can you do|who are you)\b[\s!.?]*$", re.I)
_CANCEL = re.compile(r"^\s*(cancel|stop|discard|never mind|nevermind|abort)\b", re.I)

ROUTE_SYSTEM = (
    "Classify a message sent to a procurement and inventory assistant.\n"
    "- analytics: a question answerable from data about vendors, purchase orders, payments, "
    "receipts, items, stock or stock movements.\n"
    "- raise_po: wants to create a purchase order or is giving details for one.\n"
    "- chit_chat: greetings, thanks, questions about the assistant, or off-topic requests.\n"
    "- unclear: cannot tell what is wanted.\n"
    "Return intent, confidence between 0 and 1, and a short reason."
)


class Intent(StrEnum):
    CANNED = "canned"
    ANALYTICS = "analytics"
    RAISE_PO = "raise_po"
    CHIT_CHAT = "chit_chat"
    CLARIFY = "clarify"


class RouteClassification(BaseModel):
    intent: Literal["analytics", "raise_po", "chit_chat", "unclear"]
    confidence: float = Field(ge=0, le=1)
    reason: str = ""


@dataclass(frozen=True)
class RouteDecision:
    intent: Intent
    confidence: float
    source: Literal["rule", "llm", "fallback"]
    po_command: str | None = None


_LABELS = {"analytics": Intent.ANALYTICS, "raise_po": Intent.RAISE_PO,
           "chit_chat": Intent.CHIT_CHAT, "unclear": Intent.CLARIFY}


class IntentRouter:
    def __init__(self, llm: LLM) -> None:
        self._llm = llm

    def route(self, text: str, *, button_id: str | None = None, po_action: str | None = None,
              has_open_draft: bool = False) -> RouteDecision:
        if button_id:
            return RouteDecision(Intent.CANNED, 1.0, "rule")
        if po_action:
            return RouteDecision(Intent.RAISE_PO, 1.0, "rule", po_command=po_action)
        if has_open_draft and _CANCEL.search(text):
            return RouteDecision(Intent.RAISE_PO, 1.0, "rule", po_command="cancel")
        if _PO_REQUEST.search(text):
            return RouteDecision(Intent.RAISE_PO, 1.0, "rule")
        if _SMALL_TALK.search(text):
            return RouteDecision(Intent.CHIT_CHAT, 1.0, "rule")

        classification = self._classify(text)
        if classification is None:
            fallback = Intent.RAISE_PO if has_open_draft else Intent.CLARIFY
            return RouteDecision(fallback, 0.0, "fallback")
        intent = _LABELS[classification.intent]
        if has_open_draft and not (intent in (Intent.ANALYTICS, Intent.CHIT_CHAT)
                                   and classification.confidence >= LEAVE_DRAFT_CONFIDENCE):
            return RouteDecision(Intent.RAISE_PO, classification.confidence, "llm")
        if classification.confidence < MIN_CONFIDENCE:
            return RouteDecision(Intent.CLARIFY, classification.confidence, "llm")
        return RouteDecision(intent, classification.confidence, "llm")

    def _classify(self, text: str) -> RouteClassification | None:
        try:
            return self._llm.structured(Task.ROUTE, system=ROUTE_SYSTEM, user=text,
                                        schema=RouteClassification)
        except LLMOutputError:
            log.warning("Router output unusable twice; asking the user to clarify")
            return None
