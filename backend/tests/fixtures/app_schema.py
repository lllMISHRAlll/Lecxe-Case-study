"""Hooks that grow with the app: migrations for the `assistant` schema and normalisation.

Each hook is a no-op until the feature it belongs to exists.
"""

from __future__ import annotations


def install(url: str) -> None:
    """Create app-owned schemas in the test database."""


def truncate(conn) -> None:
    """Clear app-owned tables between seeds."""


def normalise(db) -> None:
    """Apply the data normalisation changes to the seeded data."""
