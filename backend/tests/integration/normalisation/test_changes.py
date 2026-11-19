"""NORM-01..09 for every change, plus change-specific checks NORM-14..16."""

import csv

import pytest
from sqlalchemy import text

from app.normalisation.changes import CHANGES, change_by_id
from app.normalisation.runner import NotConfirmedError, Runner, VerificationFailedError

EXPECTED_ROWS = {"001": 9, "002": 5, "003": 3, "004": 3, "005": 2, "006": 2, "007": 1}


def q(db, sql, **params):
    with db.read_engine.connect() as conn:
        return conn.execute(text(sql), params).all()


def snapshot(db, change):
    cols = ", ".join(f"{c.column}::text" for c in change.columns)
    return q(db, f"select id, {cols} from {change.table} order by id")


@pytest.fixture
def runner(fresh_raw_db, tmp_path, clock):
    return Runner(fresh_raw_db, changes_dir=tmp_path / "changes",
                  log_path=tmp_path / "DATA_CHANGES.md", clock=clock, target_label="test DB")


def test_there_are_seven_changes_numbered_in_order():
    assert [c.id for c in CHANGES] == ["001", "002", "003", "004", "005", "006", "007"]


@pytest.mark.parametrize("change_id", EXPECTED_ROWS)
def test_norm_01_dry_run_counts_and_changes_nothing(runner, fresh_raw_db, change_id):
    change = change_by_id(change_id)
    before = snapshot(fresh_raw_db, change)

    preview = runner.dry_run(change)

    assert len(preview.rows) == EXPECTED_ROWS[change_id]
    assert snapshot(fresh_raw_db, change) == before


@pytest.mark.parametrize("change_id", EXPECTED_ROWS)
def test_norm_02_to_08_apply_backup_verify_idempotent_rollback_log(
        runner, fresh_raw_db, tmp_path, change_id):
    change = change_by_id(change_id)
    before = snapshot(fresh_raw_db, change)

    result = runner.apply(change, confirmed=True)

    folder = tmp_path / "changes" / change.folder
    # NORM-02 backup holds key and old values of every changed row
    with (folder / "backup.csv").open() as fh:
        backup = list(csv.DictReader(fh))
    assert len(backup) == EXPECTED_ROWS[change_id]
    assert set(backup[0]) == {"id", *(c.column for c in change.columns)}
    # NORM-03 exactly the expected rows changed
    assert result.rows_changed == EXPECTED_ROWS[change_id]
    after = snapshot(fresh_raw_db, change)
    assert sum(1 for b, a in zip(before, after, strict=True) if b != a) == EXPECTED_ROWS[change_id]
    # NORM-04 verify passed (no exception) and files are written for audit
    for name in ("apply.sql", "verify.sql", "rollback.sql"):
        assert (folder / name).exists()
    # NORM-05 running again changes nothing
    assert runner.apply(change, confirmed=True).rows_changed == 0
    # NORM-08 change log entry
    log = (tmp_path / "DATA_CHANGES.md").read_text()
    assert f"## {change.id} " in log
    assert change.table in log
    assert f"Rows changed: {EXPECTED_ROWS[change_id]}" in log
    assert "rollback" in log.lower()
    # NORM-06 rollback restores every row exactly
    runner.rollback(change)
    assert snapshot(fresh_raw_db, change) == before


def test_norm_07_failing_verify_rolls_back_everything(runner, fresh_raw_db):
    change = change_by_id("001").with_verify_sql("select 1")
    before = snapshot(fresh_raw_db, change)

    with pytest.raises(VerificationFailedError):
        runner.apply(change, confirmed=True)

    assert snapshot(fresh_raw_db, change) == before


def test_norm_09_apply_refuses_without_confirmation(runner, fresh_raw_db):
    change = change_by_id("001")
    before = snapshot(fresh_raw_db, change)

    with pytest.raises(NotConfirmedError):
        runner.apply(change)

    assert snapshot(fresh_raw_db, change) == before


def test_norm_13_unknown_spellings_are_reported_not_changed(runner, fresh_raw_db):
    with fresh_raw_db.write_engine.begin() as conn:
        conn.execute(text("update proc_po_lines set unit = 'barrel' where position = 1 and "
                          "unit = 'pcs'"))
    preview = runner.dry_run(change_by_id("001"))

    assert any("barrel" in finding for finding in preview.findings)
    assert all(row["new"]["unit"] != "barrel" for row in preview.rows)


def test_norm_14_item_names_lose_extra_spaces_only(runner, fresh_raw_db):
    runner.apply(change_by_id("005"), confirmed=True)

    names = {r[0] for r in q(fresh_raw_db, "select name from inv_items")}
    assert "Relay – 240V, 2 Pole" in names
    assert "Hex Nut M8" in names
    assert "MS Tube – 25×40×2mm" in names


def test_norm_14_trim_collision_is_skipped_and_reported(runner, fresh_raw_db):
    preview = runner.dry_run(change_by_id("005"))
    assert any("BO-EL-0002" in f for f in preview.findings)

    runner.apply(change_by_id("005"), confirmed=True)

    assert q(fresh_raw_db, "select name from inv_items where item_code = 'BO-EL-0002'")[0][0] \
        == "Electromagnet Solenoid "


def test_norm_15_null_date_lists_become_empty_lists(runner, fresh_raw_db):
    runner.apply(change_by_id("006"), confirmed=True)
    runner.apply(change_by_id("007"), confirmed=True)

    assert q(fresh_raw_db, "select count(*) from proc_purchase_orders where "
                           "expected_delivery_date is null or expected_dispatch_date is null")[0][0] == 0
    assert q(fresh_raw_db, "select expected_delivery_date::text from proc_purchase_orders "
                           "where po_number = 'PO-2026-0003'")[0][0] == '["2026-08-20", "2026-08-25"]'


def test_empty_payment_term_becomes_null(runner, fresh_raw_db):
    runner.apply(change_by_id("002"), confirmed=True)

    assert q(fresh_raw_db, "select payment_terms from proc_purchase_orders "
                           "where po_number = 'PO-2026-0005'")[0][0] is None


def test_norm_16_existing_unique_index_rejects_duplicate_po_numbers(fresh_raw_db):
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError), fresh_raw_db.write_engine.begin() as conn:
        conn.execute(text("update proc_purchase_orders set po_number = 'PO-2026-0001' "
                          "where po_number = 'PO-2026-0002'"))


def test_apply_all_in_order_matches_the_db_fixture(db):
    units = {r[0] for r in q(db, "select distinct unit from proc_po_lines")}
    assert units <= {"pcs", "kg", "set", "ltr", "mtr"}
