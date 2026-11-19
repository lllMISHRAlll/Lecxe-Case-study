"""Data dictionary: the business meaning of every table and column the assistant may query.

This is the schema text the LLM sees, so descriptions are written for SQL accuracy.
`sensitive` marks columns that must be masked or relabelled before leaving the app.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Sensitivity = Literal["staff", "address", "free_text"] | None

V, TXT, TS, NUM, DBL, INT, BOOL, JSN, DATE = (
    "character varying", "text", "timestamp without time zone", "numeric", "double precision",
    "integer", "boolean", "json", "date",
)


@dataclass(frozen=True)
class ColumnDoc:
    type: str
    description: str
    values: tuple[str, ...] = ()
    sensitive: Sensitivity = None


@dataclass(frozen=True)
class TableDoc:
    name: str
    description: str
    columns: dict[str, ColumnDoc] = field(default_factory=dict)


def C(type_: str, description: str, *values: str, sensitive: Sensitivity = None) -> ColumnDoc:
    return ColumnDoc(type_, description, tuple(values), sensitive)


ID = C(V, "Primary key (UUID text).")
CREATED = C(TS, "When the row was created.")
UPDATED = C(TS, "When the row was last updated.")
DATE_LIST_NOTE = (
    "JSON list of ISO dates, e.g. [\"2026-08-20\"]. Empty list [] when unknown. "
    "Read the first date with (col->>0)::date."
)

_tables = [
    TableDoc("inv_categories", "Top-level item categories.", {
        "id": ID,
        "name": C(V, "Category name.", "Raw Material", "Bought Out", "Finished Goods",
                  "Sub-Assembly"),
        "short_code": C(V, "Code used in item codes.", "RM", "BO", "FG", "SUB"),
        "position": C(INT, "Display order."),
        "created_at": CREATED,
    }),
    TableDoc("inv_sub_categories", "Second-level categories, each under one category.", {
        "id": ID,
        "name": C(V, "Sub-category name, e.g. Metal, Electrical, Consumable."),
        "short_code": C(V, "Short code."),
        "category_id": C(V, "FK to inv_categories.id."),
        "position": C(INT, "Display order."),
        "created_at": CREATED,
    }),
    TableDoc("inv_sub_categories_2", "Third-level categories with naming conventions.", {
        "id": ID,
        "name": C(V, "Third-level category name, e.g. 'Fastener – Nut'."),
        "short_code": C(V, "Short code."),
        "sub_category_id": C(V, "FK to inv_sub_categories.id."),
        "source_id": C(V, "Reference in the source catalogue."),
        "standard": C(TXT, "Engineering standards that apply, e.g. ISO 4032."),
        "description": C(TXT, "Description."),
        "naming_convention": C(TXT, "Template for item names in this category."),
        "convention_notes": C(TXT, "Notes on the naming convention."),
        "examples": C(TXT, "Example item names."),
        "position": C(INT, "Display order."),
        "created_at": CREATED,
        "hsn_code": C(V, "Default HSN tax code."),
        "nomenclature_fields": C(TXT, "Fields used in the naming template."),
        "nomenclature_version": C(INT, "Version of the naming template."),
        "cut_shape": C(V, "Cut shape for raw material."),
        "cut_formula": C(TXT, "Formula for cut sizes."),
    }),
    TableDoc("inv_items", "Item master: everything that is bought, stocked or sold.", {
        "id": ID,
        "item_code": C(V, "Unique item code, e.g. RM-MT-0046 or BO-EL-0199."),
        "name": C(V, "Unique item name. Use ILIKE for searches."),
        "category_id": C(V, "FK to inv_categories.id. NULL for some items: show as "
                            "'Uncategorised'."),
        "sub_category_id": C(V, "FK to inv_sub_categories.id. May be NULL."),
        "sub_category_2_id": C(V, "FK to inv_sub_categories_2.id. May be NULL."),
        "status": C(V, "Item status.", "active", "inactive"),
        "unit": C(V, "Stock unit.", "pcs", "kg", "set", "roll", "pair", "mtr", "ltr"),
        "hsn_code": C(V, "HSN tax code, often NULL."),
        "notes": C(TXT, "Free-text notes.", sensitive="free_text"),
        "specifications": C(TXT, "Free-text specifications.", sensitive="free_text"),
        "alt_units": C(TXT, "Alternative units, usually empty."),
        "is_spare": C(BOOL, "True for spare parts."),
    }),
    TableDoc("inv_locations", "Warehouses and storage locations.", {
        "id": ID,
        "name": C(V, "Location name, e.g. '132-1', 'C-84'. 'Unassigned' is an inactive "
                     "placeholder."),
        "address": C(TXT, "Address.", sensitive="address"),
        "is_active": C(BOOL, "False for retired locations."),
        "created_at": CREATED,
    }),
    TableDoc("inv_current_stock", "Current quantity of each item at each location. Items with "
                                  "no row here have zero stock everywhere.", {
        "id": ID,
        "item_id": C(V, "Item (inv_items.id). No FK, so LEFT JOIN from inv_items."),
        "location_id": C(V, "FK to inv_locations.id."),
        "quantity": C(DBL, "Quantity on hand in the item's stock unit. 0 means out of stock."),
        "min_stock_level": C(DBL, "Reorder level. Currently never set (always NULL)."),
        "max_stock_level": C(DBL, "Maximum level. Currently never set (always NULL)."),
        "last_transaction_at": C(TS, "Time of the last stock movement."),
        "updated_at": UPDATED,
    }),
    TableDoc("inv_issued_to_targets", "Teams or areas that stock is issued to.", {
        "id": ID,
        "name": C(V, "Target name, e.g. 'D132 Shop Floor', 'Dispatch team'."),
        "is_active": C(BOOL, "False for retired targets."),
        "created_at": CREATED,
    }),
    TableDoc("inv_transactions", "Stock movements. Quantity is always positive; the type says "
                                 "the direction.", {
        "id": ID,
        "item_id": C(V, "Item (inv_items.id). No FK."),
        "location_id": C(V, "FK to inv_locations.id."),
        "transaction_type": C(V, "Direction of the movement.", "inbound", "outbound",
                              "transfer_in", "transfer_out"),
        "quantity": C(DBL, "Quantity moved, positive."),
        "reference_type": C(V, "What caused the movement.", "purchase_order",
                            "unexpected_receipt", "warehouse_issue", "transfer"),
        "reference_id": C(V, "Id of the source record."),
        "transfer_location_id": C(V, "Other location for transfers."),
        "unit_cost": C(DBL, "Cost per unit for inbound movements. Often NULL."),
        "notes": C(TXT, "Free-text notes.", sensitive="free_text"),
        "created_by": C(V, "Staff member who recorded it.", sensitive="staff"),
        "created_at": C(TS, "When the movement happened."),
        "currency": C(V, "Currency of unit_cost.", "INR"),
        "issued_to_id": C(V, "FK-like link to inv_issued_to_targets.id for outbound issues."),
    }),
    TableDoc("proc_vendors", "Suppliers.", {
        "id": ID,
        "name": C(V, "Unique vendor name. Use ILIKE for searches."),
        "code": C(V, "Vendor code. Currently always empty."),
        "city": C(V, "City."),
        "payment_terms": C(V, "Default payment terms, canonical wording, e.g. '30 Days "
                              "Credit'. NULL for some vendors."),
        "is_active": C(BOOL, "False for inactive vendors."),
        "created_by": C(V, "Staff member who created it.", sensitive="staff"),
        "created_at": CREATED,
        "updated_at": UPDATED,
    }),
    TableDoc("proc_purchase_orders", "Purchase order headers.", {
        "id": ID,
        "po_number": C(V, "Unique PO number, format PO-YYYY-NNNN."),
        "vendor_id": C(V, "FK to proc_vendors.id."),
        "status": C(V, "Receiving status.", "placed", "partial", "received"),
        "placed_on": C(DATE, "Date the PO was placed."),
        "currency": C(V, "Currency of all amounts on the PO.", "INR", "USD"),
        "subtotal": C(NUM, "Sum of line subtotals."),
        "tax_amount": C(NUM, "Total tax."),
        "total_amount": C(NUM, "Grand total in the PO currency. Convert USD before adding to "
                               "INR totals."),
        "payment_terms": C(V, "Payment terms, canonical wording. May be NULL."),
        "delivery_location_id": C(V, "Delivery location (inv_locations.id). Usually NULL."),
        "ship_to_address": C(TXT, "Ship-to address.", sensitive="address"),
        "custom_fields": C(TXT, "JSON text of extra fields."),
        "created_by": C(V, "Staff member who raised it.", sensitive="staff"),
        "created_at": CREATED,
        "updated_at": UPDATED,
        "expected_delivery_date": C(JSN, "Expected delivery dates. " + DATE_LIST_NOTE),
        "expected_dispatch_date": C(JSN, "Expected dispatch dates. " + DATE_LIST_NOTE),
    }),
    TableDoc("proc_po_lines", "Purchase order lines.", {
        "id": ID,
        "po_id": C(V, "FK to proc_purchase_orders.id."),
        "inv_item_id": C(V, "Item (inv_items.id). No FK."),
        "quantity_ordered": C(NUM, "Quantity ordered, in the line unit."),
        "quantity_received": C(NUM, "Quantity received so far. Pending = ordered - received."),
        "unit": C(V, "Purchase unit. Usually the item's stock unit; when different (e.g. kg "
                     "for an item stocked in pcs) quantities are not comparable.",
                  "pcs", "kg", "set", "ltr", "mtr"),
        "unit_price": C(NUM, "Price per purchase unit in the PO currency."),
        "tax_percentage": C(NUM, "Tax rate in percent. Currently always 0."),
        "line_subtotal": C(NUM, "quantity_ordered * unit_price."),
        "line_tax": C(NUM, "Tax on the line."),
        "line_total": C(NUM, "Line total in the PO currency."),
        "notes": C(TXT, "Free-text notes.", sensitive="free_text"),
        "position": C(INT, "Line number on the PO."),
        "custom_fields": C(TXT, "JSON text of extra fields."),
        "created_at": CREATED,
        "updated_at": UPDATED,
        "is_regularised": C(BOOL, "True when a receiving mismatch was regularised."),
        "expected_delivery_date": C(JSN, "Line-level expected delivery dates, usually []. "
                                         + DATE_LIST_NOTE),
        "expected_dispatch_date": C(JSN, "Line-level expected dispatch dates, usually []. "
                                         + DATE_LIST_NOTE),
    }),
    TableDoc("proc_po_payment_tranches", "Payment schedule of a PO, one row per instalment.", {
        "id": ID,
        "po_id": C(V, "PO (proc_purchase_orders.id). No FK."),
        "sequence": C(INT, "Order of the instalment, from 0."),
        "stage": C(V, "Instalment label, e.g. 'Advance', '30 Days Credit'."),
        "percentage": C(NUM, "Share of the PO total, in percent."),
        "amount": C(NUM, "Amount. Usually NULL: compute percentage * total_amount / 100."),
        "is_advance": C(BOOL, "True for advance payments."),
        "blocks_dispatch": C(BOOL, "True if the vendor won't dispatch until this is paid."),
        "due_basis": C(V, "What the due date counts from.", "advance", "dispatch", "credit"),
        "due_offset_days": C(INT, "Days after the due basis."),
        "source": C(V, "How the tranche was created.", "extraction", "assistant"),
        "cleared_at": C(TS, "When it was paid. NULL means unpaid."),
        "cleared_by": C(V, "Staff member who cleared it.", sensitive="staff"),
        "created_at": CREATED,
        "updated_at": UPDATED,
    }),
    TableDoc("proc_po_receipts", "Goods received against PO lines.", {
        "id": ID,
        "po_line_id": C(V, "FK to proc_po_lines.id."),
        "quantity": C(NUM, "Quantity received."),
        "location_id": C(V, "Location received into."),
        "notes": C(TXT, "Free-text notes.", sensitive="free_text"),
        "inv_transaction_id": C(V, "Matching inbound stock movement."),
        "received_by": C(V, "Staff member who received it.", sensitive="staff"),
        "received_at": C(TS, "When the goods arrived."),
    }),
    TableDoc("proc_po_line_regularisations", "Corrections where received quantity or amount "
                                             "did not match the PO line.", {
        "id": ID,
        "po_id": C(V, "FK to proc_purchase_orders.id."),
        "po_line_id": C(V, "FK to proc_po_lines.id."),
        "ordered_qty": C(NUM, "Quantity ordered."),
        "received_qty_before": C(NUM, "Received before the correction."),
        "regularised_qty": C(NUM, "Quantity added or removed by the correction."),
        "received_qty_after": C(NUM, "Received after the correction."),
        "qty_variance": C(NUM, "received_qty_after - ordered_qty."),
        "unit_price": C(NUM, "Unit price."),
        "actual_amount": C(NUM, "Amount for what was actually received."),
        "expected_amount": C(NUM, "Amount for what was ordered."),
        "amount_variance": C(NUM, "actual_amount - expected_amount."),
        "notes": C(TXT, "Reason.", sensitive="free_text"),
        "inv_transaction_id": C(V, "Related stock movement."),
        "regularised_by": C(V, "Staff member.", sensitive="staff"),
        "regularised_at": C(TS, "When it was corrected."),
        "reviewed_by": C(V, "Reviewer.", sensitive="staff"),
        "reviewed_at": C(TS, "When it was reviewed."),
        "review_notes": C(TXT, "Review notes.", sensitive="free_text"),
    }),
    TableDoc("proc_unexpected_receipt_headers", "A delivery that arrived without a matching PO.", {
        "id": ID,
        "received_by": C(V, "Staff member.", sensitive="staff"),
        "received_at": C(TS, "When it arrived."),
        "notes": C(TXT, "Notes.", sensitive="free_text"),
        "vendor_name": C(V, "Vendor name as written on the delivery (text, not an id)."),
    }),
    TableDoc("proc_unexpected_receipts", "Items in a delivery that arrived without a PO.", {
        "id": ID,
        "inv_item_id": C(V, "Item (inv_items.id)."),
        "quantity": C(NUM, "Quantity received."),
        "location_id": C(V, "Location received into."),
        "notes": C(TXT, "Notes.", sensitive="free_text"),
        "inv_transaction_id": C(V, "Matching inbound stock movement."),
        "received_by": C(V, "Staff member.", sensitive="staff"),
        "received_at": C(TS, "When it arrived."),
        "resolved_po_id": C(V, "PO it was later matched to. NULL means still to reconcile."),
        "resolved_by": C(V, "Staff member who matched it.", sensitive="staff"),
        "resolved_at": C(TS, "When it was matched."),
        "header_id": C(TXT, "FK to proc_unexpected_receipt_headers.id."),
    }),
]

DICTIONARY: dict[str, TableDoc] = {t.name: t for t in _tables}


def sensitive_columns(kind: str) -> set[str]:
    """Column names of a sensitivity kind across all tables."""
    return {c for t in _tables for c, doc in t.columns.items() if doc.sensitive == kind}
