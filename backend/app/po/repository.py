"""Writes a confirmed PO: header, lines and payment tranches in one transaction.

* PO numbers continue the company format PO-YYYY-NNNN, taken under an advisory lock.
  The unique index on po_number catches a clash with another system; we retry once.
* The idempotency key is stored in custom_fields, so a repeated confirm returns the same PO.
* Vendor and items are re-checked inside the transaction (there are no foreign keys).
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import Connection, Engine, text
from sqlalchemy.exc import IntegrityError

from app.auth.users import User
from app.core.clock import Clock
from app.po.models import PODraft
from app.po.rules import review
from app.po.terms import tranches_for
from app.po.totals import draft_totals, line_totals

PO_NUMBER_LOCK = 82317701  # pg_advisory_xact_lock key for PO numbering


class POCreateError(RuntimeError):
    """The PO could not be created; the message is safe to show to the user."""


@dataclass(frozen=True)
class CreatedPO:
    po_id: str
    po_number: str
    total_amount: Decimal
    currency: str
    created: bool


class PORepository:
    def __init__(self, engine: Engine, *, clock: Clock) -> None:
        self._engine = engine
        self._clock = clock

    def create(self, draft: PODraft, user: User) -> CreatedPO:
        rev = review(draft)
        if not rev.complete:
            raise POCreateError("The PO is missing details: " +
                                ", ".join([*rev.missing, *rev.errors]))
        for attempt in range(2):
            try:
                with self._engine.begin() as conn:
                    return self._create_in(conn, draft, user)
            except IntegrityError as exc:
                if "po_number" not in str(exc):
                    raise
                if attempt == 1:
                    raise POCreateError(
                        "Couldn't reserve a free PO number. Please try again.") from exc
        raise AssertionError("unreachable")  # pragma: no cover

    # ------------------------------------------------------------------ steps

    def _create_in(self, conn: Connection, draft: PODraft, user: User) -> CreatedPO:
        conn.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": PO_NUMBER_LOCK})
        existing = self.find_by_idempotency_key(conn, draft.idempotency_key)
        if existing:
            return existing
        self.recheck_references(conn, draft)
        now = self._clock.now().astimezone(UTC).replace(tzinfo=None)
        po_id = str(uuid.uuid4())
        po_number = self.next_number(conn, self._clock.today().year)
        totals = self.insert_header(conn, po_id, po_number, draft, user, now)
        self.insert_lines(conn, po_id, draft, now)
        self.insert_tranches(conn, po_id, draft, now)
        return CreatedPO(po_id, po_number, totals, draft.currency, created=True)

    def find_by_idempotency_key(self, conn: Connection, key: str) -> CreatedPO | None:
        row = conn.execute(text(
            "SELECT id, po_number, total_amount, currency FROM proc_purchase_orders "
            "WHERE (CASE WHEN custom_fields LIKE '{%' "
            "THEN custom_fields::jsonb ->> 'idempotency_key' END) = :key"), {"key": key}).first()
        if row is None:
            return None
        return CreatedPO(row.id, row.po_number, row.total_amount, row.currency, created=False)

    def recheck_references(self, conn: Connection, draft: PODraft) -> None:
        assert draft.vendor is not None
        vendor = conn.execute(text("SELECT is_active FROM proc_vendors WHERE id = :id"),
                              {"id": draft.vendor.id}).first()
        if vendor is None or not vendor.is_active:
            raise POCreateError(f"{draft.vendor.name} is no longer an active vendor.")
        for line in draft.lines:
            assert line.item is not None
            item = conn.execute(text("SELECT status FROM inv_items WHERE id = :id"),
                                {"id": line.item.id}).first()
            if item is None or item.status != "active":
                raise POCreateError(f"{line.item.name} is no longer an active item.")

    def next_number(self, conn: Connection, year: int) -> str:
        highest = conn.execute(text(
            "SELECT MAX(CAST(substring(po_number FROM '^PO-[0-9]{4}-([0-9]+)$') AS integer)) "
            "FROM proc_purchase_orders WHERE po_number ~ :pattern"),
            {"pattern": f"^PO-{year}-[0-9]+$"}).scalar()
        return f"PO-{year}-{(highest or 0) + 1:04d}"

    def insert_header(self, conn: Connection, po_id: str, po_number: str, draft: PODraft,
                      user: User, now: datetime) -> Decimal:
        totals = draft_totals(draft.lines)
        assert draft.vendor is not None
        conn.execute(text(
            "INSERT INTO proc_purchase_orders (id, po_number, vendor_id, status, placed_on, "
            "currency, subtotal, tax_amount, total_amount, payment_terms, delivery_location_id, "
            "ship_to_address, custom_fields, created_by, created_at, updated_at, "
            "expected_delivery_date, expected_dispatch_date) VALUES (:id, :po_number, "
            ":vendor_id, 'placed', :placed_on, :currency, :subtotal, :tax, :total, :terms, "
            ":location_id, NULL, :custom_fields, :created_by, :now, :now, "
            "CAST(:expected AS json), CAST('[]' AS json))"),
            {"id": po_id, "po_number": po_number, "vendor_id": draft.vendor.id,
             "placed_on": draft.placed_on or self._clock.today(), "currency": draft.currency,
             "subtotal": totals.subtotal, "tax": totals.tax, "total": totals.total,
             "terms": draft.payment_terms,
             "location_id": draft.delivery_location.id if draft.delivery_location else None,
             "custom_fields": json.dumps({"created_via": "ai-assistant",
                                          "idempotency_key": draft.idempotency_key}),
             "created_by": user.id, "now": now,
             "expected": json.dumps([draft.expected_delivery_date.isoformat()]
                                    if draft.expected_delivery_date else [])})
        return totals.total

    def insert_lines(self, conn: Connection, po_id: str, draft: PODraft, now: datetime) -> None:
        for line in draft.lines:
            assert line.item is not None
            totals = line_totals(line)
            conn.execute(text(
                "INSERT INTO proc_po_lines (id, po_id, inv_item_id, quantity_ordered, "
                "quantity_received, unit, unit_price, tax_percentage, line_subtotal, line_tax, "
                "line_total, notes, position, custom_fields, created_at, updated_at, "
                "is_regularised, expected_delivery_date, expected_dispatch_date) VALUES (:id, "
                ":po_id, :item_id, :qty, 0, :unit, :price, :tax_pct, :subtotal, :tax, :total, "
                "NULL, :position, '{}', :now, :now, false, CAST('[]' AS json), "
                "CAST('[]' AS json))"),
                {"id": str(uuid.uuid4()), "po_id": po_id, "item_id": line.item.id,
                 "qty": line.quantity, "unit": line.unit or line.item.unit,
                 "price": line.unit_price, "tax_pct": line.tax_percentage,
                 "subtotal": totals.subtotal, "tax": totals.tax, "total": totals.total,
                 "position": line.position, "now": now})

    def insert_tranches(self, conn: Connection, po_id: str, draft: PODraft,
                        now: datetime) -> None:
        assert draft.payment_terms is not None
        for sequence, tranche in enumerate(tranches_for(draft.payment_terms)):
            conn.execute(text(
                "INSERT INTO proc_po_payment_tranches (id, po_id, sequence, stage, percentage, "
                "amount, is_advance, blocks_dispatch, due_basis, due_offset_days, source, "
                "cleared_at, cleared_by, created_at, updated_at) VALUES (:id, :po_id, :seq, "
                ":stage, :pct, NULL, :advance, :blocks, :basis, :days, 'assistant', NULL, NULL, "
                ":now, :now)"),
                {"id": str(uuid.uuid4()), "po_id": po_id, "seq": sequence,
                 "stage": tranche.stage, "pct": tranche.percentage,
                 "advance": tranche.is_advance, "blocks": tranche.blocks_dispatch,
                 "basis": tranche.due_basis, "days": tranche.due_offset_days, "now": now})
