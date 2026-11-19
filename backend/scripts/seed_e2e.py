"""Creates a seeded, normalised database for end-to-end tests and local demos.

    uv run python -m scripts.seed_e2e            # database "assistant_e2e" on the test server
"""

from __future__ import annotations

import sys

import psycopg

from app.core.config import get_settings
from tests.fixtures.database import TestDatabase


def main(name: str = "assistant_e2e") -> str:
    admin = get_settings().test_database_url
    database = TestDatabase(admin, name)
    with psycopg.connect(admin, autocommit=True) as conn:
        conn.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
        conn.execute(f'CREATE DATABASE "{name}"')
    TestDatabase.load_schema(database)
    database.after_schema()
    database.reset(normalised=True)
    database.handle().dispose()
    print(database.url)
    return database.url


if __name__ == "__main__":
    main(*sys.argv[1:])
