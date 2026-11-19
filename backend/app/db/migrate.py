"""Runs the assistant-schema migrations programmatically (no secrets in alembic.ini).

    uv run python -m app.db.migrate            # upgrade the company DB to head
"""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

MIGRATIONS = Path(__file__).parent / "migrations"


def _config(url: str, sslmode: str) -> Config:
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS))
    config.attributes["url"] = url
    config.attributes["sslmode"] = sslmode
    return config


def upgrade(url: str, revision: str = "head", *, sslmode: str = "disable") -> None:
    command.upgrade(_config(url, sslmode), revision)


def downgrade(url: str, revision: str, *, sslmode: str = "disable") -> None:
    command.downgrade(_config(url, sslmode), revision)


if __name__ == "__main__":
    from app.core.config import get_settings

    settings = get_settings()
    upgrade(settings.database_url.get_secret_value(), sslmode=settings.database_sslmode)
    print("assistant schema is up to date")
