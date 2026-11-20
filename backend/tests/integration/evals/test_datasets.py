"""The golden eval files must be valid: every reference SQL runs and passes the validator."""

import pytest

from app.auth.roles import Role
from app.sql.executor import QueryExecutor
from app.sql.validator import SqlValidator
from evals.turn import ROLES, load_role_cases

ROLE_CASES = [(role, c) for role in ROLES for c in load_role_cases(role) if c["kind"] == "data"]


@pytest.mark.parametrize("role,case", ROLE_CASES, ids=[c["id"] for _, c in ROLE_CASES])
def test_role_golden_sql_is_valid_for_that_role_and_returns_rows(db, role, case):
    validated = SqlValidator(row_cap=500).validate(case["reference_sql"], Role(role))
    assert QueryExecutor(db.read_engine, row_cap=500).run(validated.sql).row_count > 0
