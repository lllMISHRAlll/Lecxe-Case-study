"""Cleans a user message before anything else sees it."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from app.guardrails.masker import Masker

MAX_CHARS = 1000
_masker = Masker()


class InputRejectedError(ValueError):
    pass


@dataclass(frozen=True)
class CleanInput:
    text: str
    masked_kinds: frozenset[str]


def preprocess(raw: str) -> CleanInput:
    text = unicodedata.normalize("NFKC", raw)
    text = "".join(
        ch if ch in "\n\t" or unicodedata.category(ch) not in ("Cc", "Cf") else " "
        for ch in text
    )
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r" (?=[ ])", "", text)
    if not text:
        raise InputRejectedError("Please type a question.")
    if len(text) > MAX_CHARS:
        raise InputRejectedError(f"Please keep questions under {MAX_CHARS} characters.")
    masked = _masker.mask_with_kinds(text)
    return CleanInput(text=masked.text, masked_kinds=masked.kinds)
