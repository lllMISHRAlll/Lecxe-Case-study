"""EVAL-01..04 against the real model (opt-in: `pytest -m eval`, needs OPENAI_API_KEY)."""

import pytest

from app.core.config import get_settings


@pytest.fixture(scope="module")
def results():
    if not get_settings().openai_api_key.get_secret_value():
        pytest.skip("OPENAI_API_KEY not set")
    from app.db.sessions import Database
    from evals.run import SUITES, make_container
    from scripts.seed_e2e import main as seed

    db = Database.connect(seed("assistant_eval"), sslmode="disable", statement_timeout_ms=5000)
    container = make_container(db)
    yield {name: suite(container) for name, suite in SUITES.items()}
    db.dispose()


@pytest.mark.parametrize("suite", ["sql", "router", "po_extract", "injection"])
def test_suite_meets_its_pass_mark(results, suite):
    result = results[suite]
    assert result.passed, f"{suite} scored {result.score:.0%}: {result.failures[:5]}"
