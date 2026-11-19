"""The eval datasets themselves must be valid: references run and pass the validator."""

import json
from pathlib import Path

import pytest

from app.auth.roles import Role
from app.sql.executor import QueryExecutor
from app.sql.validator import SqlValidator

DATASETS = Path(__file__).resolve().parents[3] / "evals" / "datasets"
SQL_CASES = json.loads((DATASETS / "sql_golden.json").read_text())


def test_dataset_sizes_match_the_plan():
    assert len(SQL_CASES) == 30
    assert len(json.loads((DATASETS / "router.json").read_text())) == 40
    assert len(json.loads((DATASETS / "po_extract.json").read_text())) == 20


@pytest.mark.parametrize("case", SQL_CASES, ids=[c["question"][:40] for c in SQL_CASES])
def test_reference_sql_is_valid_and_returns_rows(db, case):
    validated = SqlValidator(row_cap=500).validate(case["reference_sql"], Role(case["role"]))
    result = QueryExecutor(db.read_engine, row_cap=500).run(validated.sql)
    assert result.row_count > 0
