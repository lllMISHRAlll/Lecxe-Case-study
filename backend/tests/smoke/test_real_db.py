"""SMOKE-01 / SMOKE-02: read-only checks against the real company database (opt-in).

    uv run pytest -m smoke
"""

import pytest
from sqlalchemy import text

from app.auth.roles import Role
from app.core.clock import SystemClock
from app.core.config import get_settings
from app.db.sessions import Database
from app.rbac.scope import tables_for
from app.sql.canned import REGISTRY, CannedContext
from app.sql.dictionary import DICTIONARY
from app.sql.executor import QueryExecutor
from tests.integration.canned.test_canned_queries import EXPECTED


@pytest.fixture(scope="module")
def real_db():
    settings = get_settings()
    url = settings.database_url.get_secret_value()
    if not url:
        pytest.skip("DATABASE_URL not set")
    db = Database.connect(url, sslmode=settings.database_sslmode, statement_timeout_ms=10_000)
    yield db
    db.dispose()


@pytest.mark.parametrize("button_id", EXPECTED)
def test_smoke_01_every_button_runs_read_only(real_db, button_id):
    query = REGISTRY.get(button_id)
    ctx = CannedContext(today=SystemClock().today(), fx_usd_inr=get_settings().fx_usd_inr)
    result = QueryExecutor(real_db.read_engine, row_cap=500).run(query.sql, query.params(ctx))
    assert result.column_names == EXPECTED[button_id][1]


def test_smoke_02_dictionary_matches_real_columns(real_db):
    tables = set().union(*(tables_for(r) for r in Role))
    with real_db.read_engine.connect() as conn:
        for table in tables:
            actual = {r[0] for r in conn.execute(text(
                "select column_name from information_schema.columns "
                "where table_schema = 'public' and table_name = :t"), {"t": table})}
            assert actual == set(DICTIONARY[table].columns), table
