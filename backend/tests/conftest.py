"""Shared fixtures. Markers are applied from the folder a test lives in."""

from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest

os.environ.setdefault("APP_ENV", "test")
os.environ["LANGSMITH_TRACING"] = "false"

FOLDER_MARKERS = {
    "unit": "unit",
    "integration": "integration",
    "api": "api",
    "graph": "graph",
    "security": "security",
    "arch": "arch",
    "smoke": "smoke",
    "evals": "eval",
}

FROZEN_NOW = datetime(2026, 11, 19, 9, 0, tzinfo=UTC)


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    tests_root = Path(__file__).parent
    for item in items:
        parts = Path(item.fspath).relative_to(tests_root).parts
        if parts and parts[0] in FOLDER_MARKERS:
            item.add_marker(getattr(pytest.mark, FOLDER_MARKERS[parts[0]]))


@pytest.fixture
def clock():
    from app.core.clock import FixedClock

    return FixedClock(FROZEN_NOW)


# ---------------------------------------------------------------- databases


@pytest.fixture(scope="session")
def test_database():
    """A fresh database with the company schema, created once per test session."""
    from tests.fixtures.database import TestDatabase

    database = TestDatabase.create()
    yield database
    database.drop()


@pytest.fixture(scope="session")
def raw_db(test_database) -> Iterator:
    """Seed data exactly as the company has it, quirks included. Read-only use."""
    test_database.reset(normalised=False)
    yield test_database.handle()
    test_database.mark_dirty()


@pytest.fixture
def fresh_raw_db(test_database) -> Iterator:
    """Raw seed reset before and after the test, for tests that write."""
    test_database.reset(normalised=False)
    yield test_database.handle()
    test_database.mark_dirty()
