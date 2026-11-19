"""Masks sensitive data before it leaves the app (LLM prompts, traces, logs).

* secrets: connection strings, API keys, JWTs, password assignments -> [SECRET]
* personal data: emails, phone numbers, UUIDs, GSTIN, PAN -> typed placeholders
* records: address columns -> [ADDRESS], staff id columns -> stable labels
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any

from app.auth.users import UserDirectory
from app.sql.dictionary import sensitive_columns

_PATTERNS: list[tuple[str, str, re.Pattern[str]]] = [
    ("secret", "[SECRET]", re.compile(
        r"\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis|amqp)://\S+", re.I)),
    ("secret", "[SECRET]", re.compile(
        r"\b(?:password|passwd|pwd|secret|api[_-]?key|access[_-]?token|token)\s*[:=]\s*\S+",
        re.I)),
    ("secret", "[SECRET]", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}")),
    ("secret", "[SECRET]", re.compile(r"\bls(?:v2)?_[A-Za-z0-9_]{20,}")),
    ("secret", "[SECRET]", re.compile(r"\b(?:ghp|gho|github_pat)_[A-Za-z0-9_]{20,}")),
    ("secret", "[SECRET]", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("secret", "[SECRET]", re.compile(r"\beyJ[\w-]+\.eyJ[\w-]+\.[\w-]+")),
    ("email", "[EMAIL]", re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")),
    ("uuid", "[ID]", re.compile(
        r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I)),
    ("gstin", "[GSTIN]", re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b")),
    ("pan", "[PAN]", re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")),
    ("phone", "[PHONE]", re.compile(r"(?<![\w+])(?:\+?91[\s-]?|0)?[6-9]\d{4}[\s-]?\d{5}(?!\w)")),
    ("phone", "[PHONE]", re.compile(
        r"(?<![\w+])\+(?!91)\d{1,3}[\s-]?\d{1,4}(?:[\s-]?\d{2,4}){2,3}(?!\w)")),
]

_ADDRESS = sensitive_columns("address")
_STAFF = sensitive_columns("staff")


@dataclass(frozen=True)
class MaskResult:
    text: str
    kinds: frozenset[str] = field(default_factory=frozenset)


class StaffLabeler:
    """Replaces staff UUIDs with names (demo users) or stable anonymous labels."""

    def __init__(self, users: UserDirectory | None = None) -> None:
        self._users = users or UserDirectory()

    def label(self, staff_id: str | None) -> str | None:
        if staff_id is None:
            return None
        user = self._users.get(staff_id)
        if user is not None:
            return user.name
        return "Staff " + hashlib.sha256(staff_id.encode()).hexdigest()[:4].upper()


class Masker:
    def mask_with_kinds(self, text: str) -> MaskResult:
        kinds: set[str] = set()
        for kind, token, pattern in _PATTERNS:
            text, count = pattern.subn(token, text)
            if count:
                kinds.add(kind)
        return MaskResult(text=text, kinds=frozenset(kinds))

    def mask(self, text: str) -> str:
        return self.mask_with_kinds(text).text

    def mask_value(self, column: str, value: Any, labeler: StaffLabeler) -> Any:
        if value is None:
            return None
        if column in _ADDRESS:
            return "[ADDRESS]"
        if column in _STAFF:
            return labeler.label(str(value))
        if isinstance(value, str):
            return self.mask(value)
        return value

    def mask_record(self, record: dict[str, Any], labeler: StaffLabeler) -> dict[str, Any]:
        return {k: self.mask_value(k, v, labeler) for k, v in record.items()}


def quote_data(text: str, limit: int = 200) -> str:
    """Fence database text so the LLM treats it as data. Truncates long values."""
    cleaned = text.replace("«", "‹").replace("»", "›")
    inner = limit - 2
    if len(cleaned) > inner:
        cleaned = cleaned[: inner - 1] + "…"
    return f"«{cleaned}»"
