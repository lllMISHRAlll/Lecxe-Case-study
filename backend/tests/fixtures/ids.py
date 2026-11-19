"""Deterministic UUIDs so expected results never change between runs."""

import uuid

_NS = uuid.UUID("6f1c1d4e-0000-4000-8000-000000000000")


def uid(name: str) -> str:
    return str(uuid.uuid5(_NS, name))
