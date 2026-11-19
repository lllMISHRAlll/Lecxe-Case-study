"""EVAL-01..04 against the real model (opt-in: `pytest -m eval`; uses LLM_PROVIDER and its key)."""

import pytest

from app.core.config import get_settings


@pytest.fixture(scope="module")
def results():
    settings = get_settings()
    key = (settings.anthropic_api_key if settings.llm_provider == "anthropic"
           else settings.openai_api_key)
    if not key.get_secret_value():
        pytest.skip(f"{settings.llm_provider.upper()}_API_KEY not set")
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
