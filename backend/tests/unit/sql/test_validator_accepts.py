import pytest

from app.auth.roles import Role
from app.sql.validator import SqlValidator

PM, WM = Role.PROCUREMENT_MANAGER, Role.WAREHOUSE_MANAGER
validator = SqlValidator(row_cap=500)

ACCEPTED = {
    "SQLV-01 simple select": "select name, city from proc_vendors where is_active order by name",
    "SQLV-02 join": "select v.name, p.po_number from proc_purchase_orders p "
                    "join proc_vendors v on v.id = p.vendor_id",
    "SQLV-03 cte": "with open_pos as (select id, vendor_id from proc_purchase_orders "
                   "where status in ('placed', 'partial')) select count(*) from open_pos",
    "SQLV-04 aggregates": "select status, count(*), sum(total_amount), avg(total_amount), "
                          "min(placed_on), max(placed_on) from proc_purchase_orders "
                          "group by status having count(*) > 1",
    "SQLV-05 functions": "select coalesce(i.unit, 'pcs'), nullif(i.hsn_code, ''), "
                         "case when p.currency = 'USD' then p.total_amount * 88 else "
                         "p.total_amount end, date_trunc('week', p.created_at), "
                         "(p.expected_delivery_date->>0)::date, current_date - p.placed_on, "
                         "round(p.total_amount, 2), lower(i.name), string_agg(i.name, ', '), "
                         "extract(day from now() - p.created_at), "
                         "json_array_length(p.expected_delivery_date), "
                         "row_number() over (order by p.placed_on) "
                         "from proc_purchase_orders p join proc_po_lines l on l.po_id = p.id "
                         "join inv_items i on i.id = l.inv_item_id "
                         "group by p.id, i.unit, i.hsn_code, i.name",
    "SQLV-06 public schema": "select name from public.proc_vendors",
    "SQLV-07 keywords in strings": "select name from inv_items where name ilike '%drop%' "
                                   "or name ilike '%delete from%'",
    "lateral json": "select p.po_number, d.value::date from proc_purchase_orders p "
                    "cross join lateral json_array_elements_text(p.expected_delivery_date) "
                    "as d(value)",
    "union": "select name from proc_vendors union all select name from inv_locations",
    "count star": "select count(*) from inv_items",
}


@pytest.mark.parametrize("sql", ACCEPTED.values(), ids=ACCEPTED.keys())
def test_accepts_safe_queries(sql):
    result = validator.validate(sql, PM)
    assert result.sql.lower().startswith(("select", "with"))


def test_reports_tables_used_excluding_ctes():
    result = validator.validate(ACCEPTED["SQLV-03 cte"], PM)
    assert result.tables == {"proc_purchase_orders"}


def test_sqlv_30_missing_limit_is_added():
    assert validator.validate("select name from proc_vendors", PM).sql.endswith("LIMIT 500")


def test_sqlv_31_limit_above_cap_is_lowered():
    assert validator.validate("select name from proc_vendors limit 10000", PM).sql.endswith(
        "LIMIT 500")


def test_small_limit_is_kept():
    assert validator.validate("select name from proc_vendors limit 5", PM).sql.endswith("LIMIT 5")


def test_limit_applies_to_whole_union():
    sql = validator.validate(ACCEPTED["union"], PM).sql
    assert sql.endswith("LIMIT 500")
    assert sql.count("LIMIT") == 1


def test_trailing_semicolon_is_tolerated():
    assert validator.validate("select name from proc_vendors;", PM).sql.endswith("LIMIT 500")


def test_warehouse_manager_can_query_stock():
    validator.validate("select quantity from inv_current_stock", WM)


def test_untokenisable_query_is_a_parse_error():
    import pytest as _pytest

    from app.sql.validator import SqlRejectedError

    with _pytest.raises(SqlRejectedError) as caught:
        validator.validate("select 'unterminated from proc_vendors", PM)
    assert caught.value.check == "parse"


def test_non_integer_limit_is_replaced_by_the_cap():
    assert validator.validate("select name from proc_vendors limit 1.5", PM).sql.endswith(
        "LIMIT 500")
