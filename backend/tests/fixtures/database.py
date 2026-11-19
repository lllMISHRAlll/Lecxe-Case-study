"""Lifecycle of the throwaway test database."""

from __future__ import annotations

import os
from pathlib import Path

import psycopg
from sqlalchemy import text

from app.core.config import get_settings
from app.db.sessions import Database
from tests.fixtures.seed import JSON_COLUMNS, TABLE_ORDER, build_seed

SCHEMA_SQL = Path(__file__).parent / "company_schema.sql"


def _with_db(url: str, name: str) -> str:
    base, _, _ = url.rpartition("/")
    return f"{base}/{name}"


class TestDatabase:
    """One database per test session. Data is re-seeded only when a test changed it."""

    __test__ = False  # not a pytest test class

    def __init__(self, admin_url: str, name: str) -> None:
        self.admin_url = admin_url
        self.name = name
        self.url = _with_db(admin_url, name)
        self._db: Database | None = None
        self._state: str | None = None  # "raw", "normalised" or None when dirty

    @classmethod
    def create(cls) -> TestDatabase:
        admin = get_settings().test_database_url
        instance = cls(admin, f"assistant_test_{os.getpid()}")
        with psycopg.connect(admin, autocommit=True) as conn:
            conn.execute(f'DROP DATABASE IF EXISTS "{instance.name}" WITH (FORCE)')
            conn.execute(f'CREATE DATABASE "{instance.name}"')
        with psycopg.connect(instance.url, autocommit=True) as conn:
            conn.execute("DROP SCHEMA public CASCADE")
            conn.execute(SCHEMA_SQL.read_text())
            conn.execute("SELECT pg_catalog.set_config('search_path', 'public', false)")
        instance.after_schema()
        return instance

    def after_schema(self) -> None:
        """Hook for app-owned schemas (migrations). Extended as the app grows."""
        from tests.fixtures import app_schema

        app_schema.install(self.url)

    def handle(self) -> Database:
        if self._db is None:
            self._db = Database.connect(self.url, sslmode="disable", statement_timeout_ms=5000)
        return self._db

    def reset(self, *, normalised: bool) -> None:
        wanted = "normalised" if normalised else "raw"
        if self._state == wanted:
            return
        with self.handle().write_engine.begin() as conn:
            from tests.fixtures import app_schema

            tables = ", ".join(f"public.{t}" for t in reversed(TABLE_ORDER))
            conn.execute(text(f"TRUNCATE {tables} CASCADE"))
            app_schema.truncate(conn)
            for table, rows in build_seed().items():
                _insert(conn, table, rows)
        if normalised:
            from tests.fixtures import app_schema

            app_schema.normalise(self.handle())
        self._state = wanted

    def mark_dirty(self) -> None:
        self._state = None

    def drop(self) -> None:
        if self._db is not None:
            self._db.dispose()
        with psycopg.connect(self.admin_url, autocommit=True) as conn:
            conn.execute(f'DROP DATABASE IF EXISTS "{self.name}" WITH (FORCE)')


def _insert(conn, table: str, rows: list[dict]) -> None:
    if not rows:
        return
    columns = list(rows[0])
    values = ", ".join(
        f"CAST(:{c} AS json)" if c in JSON_COLUMNS else f":{c}" for c in columns
    )
    conn.execute(
        text(f"INSERT INTO public.{table} ({', '.join(columns)}) VALUES ({values})"), rows
    )
