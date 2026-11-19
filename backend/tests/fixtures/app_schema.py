"""Hooks for app-owned parts of the test database: migrations and normalisation."""

from __future__ import annotations

from sqlalchemy import text


def install(url: str) -> None:
    """Create the assistant schema with the real migrations."""
    from app.db.migrate import upgrade

    upgrade(url, sslmode="disable")


def truncate(conn) -> None:
    conn.execute(text("TRUNCATE assistant.messages, assistant.po_drafts, "
                      "assistant.conversations CASCADE"))


def normalise(db) -> None:
    """Apply every data normalisation change to the seeded data, without writing files."""
    from app.core.clock import SystemClock
    from app.normalisation.runner import Runner

    Runner(db, changes_dir=None, log_path=None, clock=SystemClock(),
           target_label="test fixture").apply_all(confirmed=True)
