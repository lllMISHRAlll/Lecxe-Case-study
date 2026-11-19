import pytest

from app.sql.explain import SqlExplainer
from app.sql.validator import SqlRejectedError


def test_valid_query_gets_a_cost(db):
    cost = SqlExplainer(db.read_engine, cost_limit=1e9).check("select name from proc_vendors")
    assert cost > 0


def test_sqlv_32_unknown_column_error_names_the_column(db):
    with pytest.raises(SqlRejectedError) as caught:
        SqlExplainer(db.read_engine, cost_limit=1e9).check("select nme from proc_vendors")
    assert "nme" in str(caught.value)
    assert caught.value.check == "explain"


def test_sqlv_33_expensive_plan_is_rejected(db):
    with pytest.raises(SqlRejectedError) as caught:
        SqlExplainer(db.read_engine, cost_limit=0.001).check(
            "select a.name from inv_items a cross join inv_items b")
    assert "narrow" in str(caught.value).lower()


def test_explain_does_not_execute_the_query(db):
    # pg_sleep would block for 5s if executed; EXPLAIN only plans it.
    SqlExplainer(db.read_engine, cost_limit=1e9).check("select pg_sleep(5)")
