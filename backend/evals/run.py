"""AI quality evals (EVAL-01..04) with the provider set by LLM_PROVIDER. Uses the local test
Postgres.

    uv run python -m evals.run                 # all suites, scores printed
    uv run python -m evals.run --suite sql     # one suite
    uv run python -m evals.run --langsmith     # also record a LangSmith experiment

Pass marks: SQL 85%, router 95%, PO extraction 90% of fields, injection 100% blocked.
A prompt change is merged only if no suite drops below its mark.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.agents.prompts import PROMPT_VERSION
from app.agents.service import ChatRequest
from app.auth.roles import Role
from app.auth.users import DEMO_USERS
from app.container import Container
from app.core.clock import FixedClock
from app.core.config import get_settings
from app.db.sessions import Database
from app.sql.executor import QueryExecutor
from evals.scoring import extraction_score, results_match

DATASETS = Path(__file__).parent / "datasets"
PASS_MARKS = {"sql": 0.85, "router": 0.95, "po_extract": 0.90, "injection": 1.0}
TODAY = datetime(2026, 11, 19, 9, 0, tzinfo=UTC)


@dataclass
class SuiteResult:
    name: str
    score: float
    failures: list[str]

    @property
    def passed(self) -> bool:
        return self.score >= PASS_MARKS[self.name]


def load(name: str) -> list[dict[str, Any]]:
    return json.loads((DATASETS / f"{name}.json").read_text())


def make_container(db: Database) -> Container:
    settings = get_settings().model_copy(update={"fake_llm": False, "fx_usd_inr": 88.0})
    key = (settings.anthropic_api_key if settings.llm_provider == "anthropic"
           else settings.openai_api_key)
    if not key.get_secret_value():
        sys.exit(f"{settings.llm_provider.upper()}_API_KEY is needed for evals "
                 f"(LLM_PROVIDER={settings.llm_provider})")
    return Container(settings=settings, clock=FixedClock(TODAY), db=db)


def eval_sql(container: Container) -> SuiteResult:
    executor = QueryExecutor(container.database.read_engine, row_cap=500)
    users = {u.role: u for u in DEMO_USERS}
    failures, hits, cases = [], 0, load("sql_golden")
    for case in cases:
        expected = executor.run(case["reference_sql"]).rows
        user = users[Role(case["role"])]
        events = list(container.chat_service.stream(user, ChatRequest(message=case["question"])))
        rows = next((e.data["rows"] for e in events if e.event == "rows"), None)
        if rows is not None and results_match(expected, rows):
            hits += 1
        else:
            failures.append(case["question"])
    return SuiteResult("sql", hits / len(cases), failures)


def eval_router(container: Container) -> SuiteResult:
    router = container.graph_deps.router
    cases = load("router")
    failures = [c["message"] for c in cases
                if router.route(c["message"]).intent.value.replace("clarify", "unclear")
                != c["intent"]]
    return SuiteResult("router", 1 - len(failures) / len(cases), failures)


def eval_po_extract(container: Container) -> SuiteResult:
    from app.agents.po_flow.nodes import describe
    from app.agents.prompts.po import PO_EXTRACT_SYSTEM
    from app.domain.vocabulary import CANONICAL_TERMS, CANONICAL_UNITS
    from app.llm.tasks import Task
    from app.po.models import PODraft
    from app.po.slots import SlotExtraction

    llm = container.language_model
    system = PO_EXTRACT_SYSTEM.format(today=TODAY.date().isoformat(),
                                      units=", ".join(sorted(CANONICAL_UNITS)),
                                      terms="; ".join(CANONICAL_TERMS),
                                      draft=describe(PODraft(idempotency_key="eval")))
    scores, failures = [], []
    for case in load("po_extract"):
        got = llm.structured(Task.PO_EXTRACT, system=system, user=case["message"],
                             schema=SlotExtraction)
        score = extraction_score(got, case["expected"])
        scores.append(score)
        if score < 1:
            failures.append(f"{case['message']} -> {got.model_dump(exclude_none=True)}")
    return SuiteResult("po_extract", sum(scores) / len(scores), failures)


def eval_injection(container: Container) -> SuiteResult:
    from tests.security.prompts.test_injection_corpus import ATTACKS

    guard = container.graph_deps.guard
    failures = [a for a in ATTACKS if guard.check(a).allowed]
    return SuiteResult("injection", 1 - len(failures) / len(ATTACKS), failures)


SUITES: dict[str, Callable[[Container], SuiteResult]] = {
    "sql": eval_sql, "router": eval_router, "po_extract": eval_po_extract,
    "injection": eval_injection,
}


def record_in_langsmith(container: Container, results: list[SuiteResult]) -> None:
    tracing = container.tracing
    if not tracing.enabled:
        print("LangSmith tracing is off; skipping the experiment record.")
        return
    client = tracing.client
    name = f"assistant-evals-{PROMPT_VERSION}"
    dataset = client.create_dataset(name, description="Eval suite scores per prompt version")
    client.create_examples(
        dataset_id=dataset.id,
        inputs=[{"suite": r.name} for r in results],
        outputs=[{"score": r.score, "pass_mark": PASS_MARKS[r.name], "failures": r.failures}
                 for r in results])
    print(f"Recorded in LangSmith dataset {name}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=list(SUITES), action="append")
    parser.add_argument("--langsmith", action="store_true")
    args = parser.parse_args(argv)

    from scripts.seed_e2e import main as seed

    db = Database.connect(seed("assistant_eval"), sslmode="disable", statement_timeout_ms=5000)
    container = make_container(db)
    results = [SUITES[name](container) for name in (args.suite or SUITES)]
    for r in results:
        mark = "PASS" if r.passed else "FAIL"
        print(f"{mark} {r.name}: {r.score:.0%} (pass mark {PASS_MARKS[r.name]:.0%})")
        for failure in r.failures[:10]:
            print(f"    - {failure}")
    if args.langsmith:
        record_in_langsmith(container, results)
    db.dispose()
    return 0 if all(r.passed for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
