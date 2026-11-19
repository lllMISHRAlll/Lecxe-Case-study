from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.db.sessions import Database
from app.sql.executor import QueryExecutor, QueryFailedError


def test_db_01_read_session_refuses_insert(db):
    with pytest.raises(DBAPIError) as caught, db.read_engine.begin() as conn:
        conn.execute(text("insert into inv_issued_to_targets (id, name, is_active, created_at) "
                          "values ('x', 'x', true, now())"))
    assert "read-only" in str(caught.value)


def test_db_02_read_session_cancels_slow_queries(test_database):
    slow = Database.connect(test_database.url, sslmode="disable", statement_timeout_ms=200)
    try:
        with pytest.raises(QueryFailedError) as caught:
            QueryExecutor(slow.read_engine, row_cap=10).run("select pg_sleep(2)")
        assert "took too long" in str(caught.value)
    finally:
        slow.dispose()


def test_db_03_results_above_the_cap_are_cut_and_flagged(db):
    result = QueryExecutor(db.read_engine, row_cap=3).run(
        "select id from inv_items order by item_code")

    assert len(result.rows) == 3
    assert result.truncated is True
    assert result.row_count == 3


def test_results_under_the_cap_are_not_flagged(db):
    result = QueryExecutor(db.read_engine, row_cap=500).run("select name from proc_vendors")
    assert result.truncated is False
    assert result.row_count == 6


def test_columns_carry_simple_types(db):
    result = QueryExecutor(db.read_engine, row_cap=5).run(
        "select po_number, total_amount, placed_on, currency = 'USD' as is_usd "
        "from proc_purchase_orders order by po_number limit 1")

    assert [c.name for c in result.columns] == ["po_number", "total_amount", "placed_on",
                                                "is_usd"]
    assert [c.type for c in result.columns] == ["text", "number", "date", "boolean"]
    assert isinstance(result.rows[0][1], Decimal)
    assert isinstance(result.rows[0][2], date)


def test_parameters_are_bound(db):
    result = QueryExecutor(db.read_engine, row_cap=5).run(
        "select name from proc_vendors where city = :city", {"city": "Chennai"})
    assert result.rows == [["Anand Engineering Pvt. Ltd."]]


def test_database_errors_become_short_messages(db):
    with pytest.raises(QueryFailedError) as caught:
        QueryExecutor(db.read_engine, row_cap=5).run("select 1/0")
    assert "division by zero" in str(caught.value)


def test_db_05_write_session_can_commit(fresh_db):
    with fresh_db.write_engine.begin() as conn:
        conn.execute(text("insert into inv_issued_to_targets (id, name, is_active, created_at) "
                          "values ('w', 'Write test', true, now())"))
    with fresh_db.read_engine.connect() as conn:
        assert conn.execute(text("select count(*) from inv_issued_to_targets "
                                 "where id = 'w'")).scalar() == 1
