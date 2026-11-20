"""Support contact details, read from `app/config/support.yaml` (not hard-coded in replies)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

DEFAULT_PATH = Path(__file__).resolve().parents[1] / "config" / "support.yaml"


def load_support_email(path: Path = DEFAULT_PATH) -> str:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return str(data["support"]["email"]).strip()


@lru_cache
def support_email() -> str:
    return load_support_email()
