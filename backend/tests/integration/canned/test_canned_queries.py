"""CAN-01..13: every button runs on the seed, returns the expected columns and rows,
passes the validator, stays fast, and is listed only for its roles."""

import time
from datetime import date
from decimal import Decimal

import pytest

from app.auth.roles import Role
from app.sql.canned import REGISTRY, CannedContext, latest_activity
from app.sql.executor import QueryExecutor
from app.sql.validator import SqlValidator

PM, BO, WM = Role.PROCUREMENT_MANAGER, Role.BUSINESS_OWNER, Role.WAREHOUSE_MANAGER
CTX = CannedContext(today=date(2026, 11, 19), fx_usd_inr=88.0)

EXPECTED = {
    # id: (roles, columns, row count)
    "pm_open_pos": ({PM}, ["po_number", "vendor", "status", "placed_on", "currency",
                           "total_amount", "age_days"], 5),
    "pm_overdue": ({PM}, ["po_number", "vendor", "status", "expected_on", "days_late",
                          "pending_qty"], 3),
    "pm_out_of_stock_in_use": ({PM}, ["item_code", "item", "unit", "issued_qty",
                                      "last_issued", "last_vendor", "last_price",
                                      "currency"], 5),
    "pm_spend_by_vendor": ({PM}, ["vendor", "pos", "spend_inr"], 5),
    "pm_fulfilment": ({PM}, ["vendor", "ordered_qty", "received_qty", "fulfilment_pct",
                             "unit_mismatch_lines"], 5),
    "pm_unexpected_receipts": ({PM}, ["vendor", "item_code", "item", "quantity", "unit",
                                      "received_on", "location"], 2),
    "pm_blocking_payments": ({PM}, ["po_number", "vendor", "stage", "percentage", "amount",
                                    "currency", "status"], 4),
    "bo_top_vendors": ({BO}, ["vendor", "pos", "spend_inr"], 5),
    "bo_spend_by_category": ({BO}, ["category", "spend_inr"], 3),
    "bo_po_pipeline": ({BO}, ["status", "pos", "value_inr"], 3),
    "bo_vendor_scorecard": ({BO}, ["vendor", "pos", "spend_inr", "fulfilment_pct",
                                   "on_time_pct"], 5),
    "bo_stock_in_out_weekly": ({BO}, ["week", "qty_in", "qty_out"], 5),
    "bo_unplanned_by_vendor": ({BO}, ["vendor", "receipts", "unresolved"], 2),
    "wm_stock_by_warehouse": ({WM}, ["warehouse", "items_in_stock", "items_out_of_stock"], 3),
    "wm_out_of_stock_in_use": ({WM}, ["item_code", "item", "unit", "issued_qty",
                                      "last_issued"], 5),
    "wm_expected_inbound": ({WM}, ["po_number", "vendor", "item_code", "item", "pending_qty",
                                   "unit", "expected_on", "line_total", "currency"], 8),
    "wm_recent_movements": ({WM}, ["moved_at", "item_code", "item", "transaction_type",
                                   "quantity", "unit", "location", "issued_to"], 12),
    "wm_consumption_by_target": ({WM}, ["issued_to", "issues", "qty"], 2),
    "wm_unexpected_receipts": ({WM}, ["vendor", "item_code", "item", "quantity", "unit",
                                      "received_on", "location"], 2),
    "wm_no_movement": ({WM}, ["item_code", "item", "category", "unit", "on_hand"], 3),
}


def run(db, button_id):
    query = REGISTRY.get(button_id)
    return QueryExecutor(db.read_engine, row_cap=500).run(query.sql, query.params(CTX))


def test_there_are_twenty_buttons_seven_six_seven():
    assert set(REGISTRY.ids()) == set(EXPECTED)
    assert [len(REGISTRY.for_role(r)) for r in (PM, BO, WM)] == [7, 6, 7]


@pytest.mark.parametrize("button_id", EXPECTED)
def test_can_01_02_runs_with_expected_columns_and_rows(db, button_id):
    _, columns, count = EXPECTED[button_id]
    result = run(db, button_id)
    assert result.column_names == columns
    assert result.row_count == count


@pytest.mark.parametrize("button_id", EXPECTED)
def test_can_03_passes_the_validator_for_its_roles(button_id):
    query = REGISTRY.get(button_id)
    assert ":" not in query.literal_sql(CTX).replace("::", "")
    for role in query.roles:
        SqlValidator(row_cap=500).validate(query.literal_sql(CTX), role)


@pytest.mark.parametrize("button_id", EXPECTED)
def test_can_04_finishes_quickly(db, button_id):
    run(db, button_id)  # warm up
    started = time.perf_counter()
    run(db, button_id)
    assert time.perf_counter() - started < 0.5


@pytest.mark.parametrize("button_id", EXPECTED)
def test_can_05_listed_only_for_its_roles(button_id):
    roles, _, _ = EXPECTED[button_id]
    assert REGISTRY.get(button_id).roles == frozenset(roles)
    for role in Role:
        assert (button_id in [q.id for q in REGISTRY.for_role(role)]) is (role in roles)


def test_spend_by_vendor_values(db):
    rows = {r["vendor"]: r for r in run(db, "pm_spend_by_vendor").records()}
    assert rows["Global Automation Inc."]["spend_inr"] == Decimal("72160.00")
    assert rows["Zenith Steels Pvt. Ltd."]["spend_inr"] == Decimal("14100.00")
    assert rows["Zenith Steels Pvt. Ltd."]["pos"] == 2


def test_overdue_lists_open_pos_past_their_date(db):
    rows = {r["po_number"]: r for r in run(db, "pm_overdue").records()}
    assert set(rows) == {"PO-2026-0002", "PO-2026-0003", "PO-2026-0010"}
    assert rows["PO-2026-0002"]["days_late"] == (date(2026, 11, 19) - date(2026, 8, 10)).days


def test_out_of_stock_in_use_shows_last_purchase(db):
    rows = {r["item_code"]: r for r in run(db, "pm_out_of_stock_in_use").records()}
    assert rows["BO-EL-0003"]["last_vendor"] == "Global Automation Inc."
    assert rows["BO-EL-0003"]["currency"] == "USD"
    assert "RM-MT-0001" not in rows  # in stock


def test_blocking_payments_compute_amount_from_percentage(db):
    rows = {r["po_number"]: r for r in run(db, "pm_blocking_payments").records()}
    assert rows["PO-2026-0010"]["amount"] == Decimal("9000.00")


def test_vendor_scorecard_on_time(db):
    rows = {r["vendor"]: r for r in run(db, "bo_vendor_scorecard").records()}
    assert rows["Zenith Steels Pvt. Ltd."]["on_time_pct"] == Decimal("100.0")
    assert rows["Anand Engineering Pvt. Ltd."]["on_time_pct"] == Decimal("33.3")  # 1 of 3


def test_stock_by_warehouse_counts(db):
    rows = {r["warehouse"]: r for r in run(db, "wm_stock_by_warehouse").records()}
    assert (rows["132-1"]["items_in_stock"], rows["132-1"]["items_out_of_stock"]) == (4, 2)


def test_can_10_latest_activity_dates(db):
    executor = QueryExecutor(db.read_engine, row_cap=5)
    assert latest_activity(executor) == {"po_placed": date(2026, 8, 19),
                                         "stock_movement": date(2026, 8, 21)}


def test_can_11_usd_converted_and_noted():
    query = REGISTRY.get("pm_spend_by_vendor")
    assert query.params(CTX)["fx"] == 88.0
    assert "88" in query.note(CTX)


def test_can_12_uncategorised_items_are_labelled(db):
    rows = {r["item_code"]: r for r in run(db, "wm_no_movement").records()}
    assert rows["NW-0001"]["category"] == "Uncategorised"


def test_can_13_unit_mismatches_are_flagged(db):
    rows = {r["vendor"]: r for r in run(db, "pm_fulfilment").records()}
    assert rows["Vanguard Electricals"]["unit_mismatch_lines"] == 1
    assert rows["Anand Engineering Pvt. Ltd."]["unit_mismatch_lines"] == 1
    assert rows["Zenith Steels Pvt. Ltd."]["unit_mismatch_lines"] == 0


def test_rbac_09_getting_another_roles_button_is_forbidden():
    from app.core.errors import Forbidden

    with pytest.raises(Forbidden):
        REGISTRY.get_for(WM, "pm_spend_by_vendor")
    assert REGISTRY.get_for(PM, "pm_spend_by_vendor").id == "pm_spend_by_vendor"


def test_unknown_button_is_not_found():
    from app.core.errors import NotFound

    with pytest.raises(NotFound):
        REGISTRY.get_for(PM, "nope")
