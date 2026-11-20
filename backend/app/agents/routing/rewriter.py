"""Turns a follow-up ("and last month?") into a standalone question using recent turns."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from pydantic import BaseModel

from app.llm.port import LLM
from app.llm.tasks import Task

log = logging.getLogger(__name__)
MAX_TURNS = 3

_FOLLOW_UP = re.compile(
    r"^\s*(and|also|what about|how about|only|now|but|instead|same|then|ok|okay|why|so)\b"
    r"|\b(it|that one|those|these|them|they|their|same|this one|above)\b"
    # "this PO", "that order", "the last PO", "the PO I just raised": a reference to something
    # from an earlier turn, with no identifier in the message itself.
    r"|\b(this|that|the\s+(?:same|last|previous|latest|recent|above))\s+"
    r"(?:po|pos|order|orders|purchase\s+orders?|vendor|vendors|item|items|receipt|payment|one)\b"
    r"|\bi\s+(?:just\s+)?(?:raised|created|made|placed)\b", re.I)

REWRITE_SYSTEM = (
    "Rewrite the user's latest message as one standalone question about procurement or "
    "inventory data, using the earlier turns only to fill in what the message refers to. "
    "Keep the user's intent and wording where possible. When the message points at something "
    "from the earlier turns (\"this PO\", \"that vendor\", \"the one I just raised\"), replace "
    "the reference with its exact identifier or name from those turns, such as the PO number. "
    "Do not answer it."
)


@dataclass(frozen=True)
class Turn:
    question: str
    answer: str


class Rewritten(BaseModel):
    question: str


def is_follow_up(text: str) -> bool:
    return len(text.split()) <= 3 or bool(_FOLLOW_UP.search(text))


class FollowUpRewriter:
    def __init__(self, llm: LLM) -> None:
        self._llm = llm

    def rewrite(self, question: str, history: list[Turn]) -> str:
        if not history or not is_follow_up(question):
            return question
        recent = history[-MAX_TURNS:]
        transcript = "\n".join(f"User: {t.question}\nAssistant: {t.answer}" for t in recent)
        prompt = f"Earlier turns:\n{transcript}\n\nLatest message: {question}"
        try:
            result = self._llm.structured(Task.REWRITE, system=REWRITE_SYSTEM, user=prompt,
                                          schema=Rewritten)
        except Exception:
            log.warning("Follow-up rewrite failed; using the original question", exc_info=True)
            return question
        return result.question.strip() or question
