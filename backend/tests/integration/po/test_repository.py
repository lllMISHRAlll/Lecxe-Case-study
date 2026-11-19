"""POR-01..10: the PO insert path against the test database."""

import json
import threading
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import text

from app.auth.users import DEMO_USERS
from app.core.clock import FixedClock
from app.po.catalog_db import DbCatalog
from app.po.models import PODraft, POLine
from app.po.repository import POCreateError, PORepository
from app.po.rules import apply_defaults

PM = DEMO_USERS[0]
NOW = datetime(2026, 11, 19, 9, 0, tzinfo=UTC)


def q(db, sql, **params):
    with db.read_engine.connect() as conn:
        return conn.execute(text(sql), params).all()


def make_draft(db, key="key-1", term="50% Advance, Balance 30 Days Credit"):
    cat = DbCatalog.load(db.read_engine)
    vendor = next(v for v in cat.vendors if v.name.startswith("Zenith"))
    tube = next(i for i in cat.items if i.code == "RM-MT-0001")
    relay = next(i for i in cat.items if i.code == "BO-EL-0001")
    draft = PODraft(idempotency_key=key, vendor=vendor, payment_terms=term,
                    expected_delivery_date=date(2026, 11, 30), lines=[
                        POLine(position=1, item=tube, quantity=Decimal(50),
                               unit_price=Decimal("120")),
                        POLine(position=2, item=relay, quantity=Decimal(10),
                               unit_price=Decimal("450"), tax_percentage=Decimal(18)),
                    ])
    return apply_defaults(draft, NOW.date())


def repo(db, now=NOW):
    return PORepository(db.write_engine, clock=FixedClock(now))


def test_por_01_next_number_continues_from_the_highest(fresh_db):
    created = repo(fresh_db).create(make_draft(fresh_db), PM)
    assert created.po_number == "PO-2026-0011"  # seed's highest is PO-2026-0010
    assert created.created is True


def test_por_02_first_po_of_a_new_year_starts_at_0001(fresh_db):
    created = repo(fresh_db, datetime(2027, 1, 2, tzinfo=UTC)).create(make_draft(fresh_db), PM)
    assert created.po_number == "PO-2027-0001"


def test_por_03_other_number_formats_are_ignored(fresh_db):
    with fresh_db.write_engine.begin() as conn:
        conn.execute(text("update proc_purchase_orders set po_number = 'PO-2026-9999-OLD' "
                          "where po_number = 'PO-2026-0006'"))
        conn.execute(text("update proc_purchase_orders set po_number = 'PO-AI-2026-5000' "
                          "where po_number = 'PO-2026-0005'"))
    assert repo(fresh_db).create(make_draft(fresh_db), PM).po_number == "PO-2026-0011"


def test_por_04_concurrent_inserts_get_different_numbers(fresh_db):
    numbers, errors = [], []

    def worker(key):
        try:
            numbers.append(repo(fresh_db).create(make_draft(fresh_db, key=key), PM).po_number)
        except Exception as exc:  # pragma: no cover - surfaced by the assert below
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(f"k{i}",)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
    assert sorted(numbers) == ["PO-2026-0011", "PO-2026-0012", "PO-2026-0013", "PO-2026-0014"]


class ClashingRepository(PORepository):
    """Hands out an existing number first, as if another system took it meanwhile."""

    def __init__(self, *args, clashes, **kwargs):
        super().__init__(*args, **kwargs)
        self.clashes = clashes

    def next_number(self, conn, year):
        if self.clashes:
            self.clashes -= 1
            return "PO-2026-0001"
        return super().next_number(conn, year)


def test_por_05_a_clash_retries_once_and_succeeds(fresh_db):
    created = ClashingRepository(fresh_db.write_engine, clock=FixedClock(NOW), clashes=1).create(
        make_draft(fresh_db), PM)
    assert created.po_number == "PO-2026-0011"


def test_por_05_a_second_clash_fails_cleanly(fresh_db):
    with pytest.raises(POCreateError):
        ClashingRepository(fresh_db.write_engine, clock=FixedClock(NOW), clashes=2).create(
            make_draft(fresh_db), PM)
    assert q(fresh_db, "select count(*) from proc_purchase_orders")[0][0] == 7


def test_por_06_07_header_lines_and_tranches_written_exactly(fresh_db):
    created = repo(fresh_db).create(make_draft(fresh_db), PM)

    header = q(fresh_db, "select status, placed_on, currency, subtotal, tax_amount, total_amount,"
                         " payment_terms, created_by, custom_fields, "
                         "expected_delivery_date::text, expected_dispatch_date::text "
                         "from proc_purchase_orders where id = :id", id=created.po_id)[0]
    assert header[:8] == ("placed", date(2026, 11, 19), "INR", Decimal("10500.00"),
                          Decimal("810.00"), Decimal("11310.00"),
                          "50% Advance, Balance 30 Days Credit", PM.id)
    assert json.loads(header[8]) == {"created_via": "ai-assistant", "idempotency_key": "key-1"}
    assert (header[9], header[10]) == ('["2026-11-30"]', "[]")

    lines = q(fresh_db, "select position, unit, quantity_ordered, quantity_received, unit_price, "
                        "tax_percentage, line_subtotal, line_tax, line_total, is_regularised "
                        "from proc_po_lines where po_id = :id order by position",
              id=created.po_id)
    assert lines == [
        (1, "kg", Decimal("50"), Decimal("0"), Decimal("120"), Decimal("0"), Decimal("6000.00"),
         Decimal("0.00"), Decimal("6000.00"), False),
        (2, "pcs", Decimal("10"), Decimal("0"), Decimal("450"), Decimal("18"),
         Decimal("4500.00"), Decimal("810.00"), Decimal("5310.00"), False),
    ]
    tranches = q(fresh_db, "select sequence, stage, percentage, amount, is_advance, "
                           "blocks_dispatch, due_basis, due_offset_days, source, cleared_at "
                           "from proc_po_payment_tranches where po_id = :id order by sequence",
                 id=created.po_id)
    assert tranches == [
        (0, "Advance", Decimal("50"), None, True, True, "advance", 0, "assistant", None),
        (1, "Balance 30 Days Credit", Decimal("50"), None, False, False, "credit", 30,
         "assistant", None),
    ]


class FailingRepository(PORepository):
    def insert_tranches(self, conn, po_id, draft, now):
        raise RuntimeError("disk full")


def test_por_08_a_failure_partway_leaves_nothing(fresh_db):
    with pytest.raises(RuntimeError):
        FailingRepository(fresh_db.write_engine, clock=FixedClock(NOW)).create(
            make_draft(fresh_db), PM)
    assert q(fresh_db, "select count(*) from proc_purchase_orders")[0][0] == 7
    assert q(fresh_db, "select count(*) from proc_po_lines")[0][0] == 11


def test_por_09_same_idempotency_key_returns_the_same_po(fresh_db):
    first = repo(fresh_db).create(make_draft(fresh_db, key="same"), PM)
    second = repo(fresh_db).create(make_draft(fresh_db, key="same"), PM)
    assert second.po_number == first.po_number
    assert second.created is False
    assert q(fresh_db, "select count(*) from proc_purchase_orders")[0][0] == 8


def test_por_10_item_removed_before_confirm_fails_cleanly(fresh_db):
    draft = make_draft(fresh_db)
    with fresh_db.write_engine.begin() as conn:
        conn.execute(text("update inv_items set status = 'inactive' where item_code = "
                          "'BO-EL-0001'"))
    with pytest.raises(POCreateError) as caught:
        repo(fresh_db).create(draft, PM)
    assert "Relay" in str(caught.value)
    assert q(fresh_db, "select count(*) from proc_purchase_orders")[0][0] == 7


def test_incomplete_draft_is_refused(fresh_db):
    draft = make_draft(fresh_db).model_copy(update={"payment_terms": None})
    with pytest.raises(POCreateError):
        repo(fresh_db).create(draft, PM)


def test_usd_po_with_single_tranche(fresh_db):
    draft = make_draft(fresh_db, term="100% Advance").model_copy(update={"currency": "USD"})
    created = repo(fresh_db).create(draft, PM)
    assert created.currency == "USD"
    assert q(fresh_db, "select count(*) from proc_po_payment_tranches where po_id = :id",
             id=created.po_id)[0][0] == 1


def test_vendor_deactivated_before_confirm_fails_cleanly(fresh_db):
    draft = make_draft(fresh_db)
    with fresh_db.write_engine.begin() as conn:
        conn.execute(text("update proc_vendors set is_active = false where name like 'Zenith%'"))
    with pytest.raises(POCreateError) as caught:
        repo(fresh_db).create(draft, PM)
    assert "Zenith" in str(caught.value)


class OtherIntegrityError(PORepository):
    def insert_lines(self, conn, po_id, draft, now):
        conn.execute(text("insert into inv_issued_to_targets (id, name, is_active, created_at) "
                          "select 'dup', name, true, now() from inv_issued_to_targets limit 1"))


def test_integrity_errors_unrelated_to_numbers_are_not_retried(fresh_db):
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        OtherIntegrityError(fresh_db.write_engine, clock=FixedClock(NOW)).create(
            make_draft(fresh_db), PM)
    assert q(fresh_db, "select count(*) from proc_purchase_orders")[0][0] == 7
