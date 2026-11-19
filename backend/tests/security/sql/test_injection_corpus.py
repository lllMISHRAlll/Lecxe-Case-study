"""SQLV-10..23 and SQLV-34: every one of these must be rejected with a clear reason."""

import pytest

from app.auth.roles import Role
from app.sql.validator import SqlRejectedError, SqlValidator

PM, WM = Role.PROCUREMENT_MANAGER, Role.WAREHOUSE_MANAGER
validator = SqlValidator(row_cap=500)

REJECTED = {
    # SQLV-10 data changes
    "insert": ("insert into proc_vendors (id, name) values ('x', 'y')", "only select"),
    "update": ("update proc_vendors set name = 'x'", "only select"),
    "delete": ("delete from proc_vendors", "only select"),
    "merge": ("merge into proc_vendors v using inv_items i on v.id = i.id "
              "when matched then delete", "only select"),
    "truncate": ("truncate proc_vendors", "only select"),
    "dml in cte": ("with d as (delete from proc_vendors returning id) select * from d",
                   "only select"),
    # SQLV-11 schema changes
    "drop": ("drop table proc_vendors", "only select"),
    "alter": ("alter table proc_vendors add column x int", "only select"),
    "create": ("create table x (a int)", "only select"),
    "grant": ("grant all on proc_vendors to public", "only select"),
    "revoke": ("revoke all on proc_vendors from public", "only select"),
    "comment on": ("comment on table proc_vendors is 'x'", "only select"),
    # SQLV-12 stacked statements
    "stacked": ("select 1; drop table proc_vendors", "one statement"),
    "stacked selects": ("select 1; select 2", "one statement"),
    # SQLV-13 comments
    "line comment": ("select name from proc_vendors -- where 1=1", "comment"),
    "block comment": ("select /* hi */ name from proc_vendors", "comment"),
    # SQLV-14 dangerous functions
    "pg_sleep": ("select pg_sleep(10)", "pg_sleep"),
    "pg_read_file": ("select pg_read_file('/etc/passwd')", "pg_read_file"),
    "lo_import": ("select lo_import('/etc/passwd')", "lo_import"),
    "dblink": ("select * from dblink('host=x', 'select 1') as t(a int)", "dblink"),
    "set_config": ("select set_config('default_transaction_read_only', 'off', false)",
                   "set_config"),
    "current_setting": ("select current_setting('server_version')", "current_setting"),
    "terminate": ("select pg_terminate_backend(1)", "pg_terminate_backend"),
    "schema-qualified function": ("select pg_catalog.pg_sleep(1)", "pg_sleep"),
    # SQLV-15 unknown function
    "unknown function": ("select my_func(name) from proc_vendors", "my_func"),
    "generate_series": ("select x from generate_series(1, 1000000000) as g(x)", "not allowed"),
    # SQLV-16 other statements
    "copy": ("copy proc_vendors to '/tmp/x'", "only select"),
    "call": ("call some_proc()", "only select"),
    "do": ("do $$ begin perform 1; end $$", "only select"),
    "lock": ("lock table proc_vendors", "only select"),
    "vacuum": ("vacuum proc_vendors", "only select"),
    "prepare": ("prepare s as select 1", "only select"),
    "execute": ("execute s", "only select"),
    "set": ("set role postgres", "only select"),
    "select into": ("select name into new_table from proc_vendors", "into"),
    # SQLV-17 row locking
    "for update": ("select name from proc_vendors for update", "lock"),
    "for share": ("select name from proc_vendors for share", "lock"),
    # SQLV-18 catalogs
    "pg_catalog": ("select usename from pg_catalog.pg_user", "pg_catalog.pg_user"),
    "information_schema": ("select table_name from information_schema.tables",
                           "information_schema.tables"),
    "bare catalog table": ("select usename from pg_user", "pg_user"),
    # SQLV-19 app schema
    "assistant schema": ("select text from assistant.messages", "assistant.messages"),
    # SQLV-22 star
    "select star": ("select * from proc_vendors", "select *"),
    "table star": ("select v.* from proc_vendors v", "select *"),
    # SQLV-23 junk
    "empty": ("   ", "empty"),
    "not sql": ("show me the money", "parse"),
    "too long": ("select name from proc_vendors where name = '" + "a" * 10_001 + "'",
                 "too long"),
}


@pytest.mark.parametrize(("sql", "reason"), REJECTED.values(), ids=REJECTED.keys())
def test_rejected_for_every_role(sql, reason):
    with pytest.raises(SqlRejectedError) as caught:
        validator.validate(sql, PM)
    assert reason.lower() in str(caught.value).lower()


SCOPE_ESCAPES = {
    # SQLV-20 out-of-scope table for the Warehouse Manager, in every position
    "direct": "select stage from proc_po_payment_tranches",
    "join": "select p.po_number from proc_purchase_orders p join proc_po_payment_tranches t "
            "on t.po_id = p.id",
    "subquery": "select po_number from proc_purchase_orders where id in "
                "(select po_id from proc_po_payment_tranches)",
    "exists": "select 1 from inv_items where exists (select 1 from proc_po_payment_tranches)",
    "cte": "with t as (select po_id from proc_po_payment_tranches) select count(*) from t",
    "union": "select name from proc_vendors union select stage from proc_po_payment_tranches",
    "scalar subquery": "select (select count(*) from proc_po_payment_tranches) as n",
    # SQLV-21 case and quoting tricks
    "quoted upper": 'select stage from "PROC_PO_PAYMENT_TRANCHES"',
    "mixed case": "select stage from Proc_Po_Payment_Tranches",
    "schema qualified": "select stage from public.proc_po_payment_tranches",
    "cte shadowing name": "with proc_vendors as (select stage from proc_po_payment_tranches) "
                          "select stage from proc_vendors",
}


@pytest.mark.parametrize("sql", SCOPE_ESCAPES.values(), ids=SCOPE_ESCAPES.keys())
def test_sqlv_20_21_out_of_scope_table_is_rejected_anywhere(sql):
    with pytest.raises(SqlRejectedError) as caught:
        validator.validate(sql, WM)
    assert "proc_po_payment_tranches" in str(caught.value).lower()


def test_sqlv_34_first_failing_check_is_reported():
    # Has a comment AND is a DELETE: the comment check runs first.
    with pytest.raises(SqlRejectedError) as caught:
        validator.validate("delete from proc_vendors -- bye", PM)
    assert "comment" in str(caught.value).lower()
    assert caught.value.check == "comments"


def test_checks_run_in_documented_order():
    from app.sql.validator import CHECK_ORDER

    assert CHECK_ORDER == ("length", "comments", "parse", "single_statement", "statement_type",
                           "clauses", "star", "tables", "functions", "limit")
