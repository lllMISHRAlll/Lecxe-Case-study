"""Hooks that grow with the app: migrations for the `assistant` schema and normalisation."""

from __future__ import annotations


def install(url: str) -> None:
    """Create app-owned schemas in the test database."""


def truncate(conn) -> None:
    """Clear app-owned tables between seeds."""


def normalise(db) -> None:
    """Apply every data normalisation change to the seeded data, without writing files."""
    from app.core.clock import SystemClock
    from app.normalisation.runner import Runner

    Runner(db, changes_dir=None, log_path=None, clock=SystemClock(),
           target_label="test fixture").apply_all(confirmed=True)
