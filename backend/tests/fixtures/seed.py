"""Seed data for the test database.

Small, but it reproduces every quirk found in the real company data:
mixed unit spellings, misspelled payment terms, empty and NULL date lists, an empty-string
payment term, a vendor without terms, items without stock rows or category, a USD order,
untrimmed item names and a name that would collide after trimming.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal

from tests.fixtures.ids import uid

STAFF_A = uid("staff-a")
STAFF_B = uid("staff-b")
T0 = datetime(2026, 4, 1, 9, 0)

JSON_COLUMNS = {"expected_delivery_date", "expected_dispatch_date"}


def _ts(day: str) -> datetime:
    return datetime.fromisoformat(day + "T10:00:00")


def _dates(values: list[str] | None) -> str | None:
    return None if values is None else json.dumps(values)


def build_seed() -> dict[str, list[dict]]:
    rows: dict[str, list[dict]] = {}

    rows["inv_categories"] = [
        dict(id=uid("cat-rm"), name="Raw Material", short_code="RM", position=1, created_at=T0),
        dict(id=uid("cat-bo"), name="Bought Out", short_code="BO", position=2, created_at=T0),
        dict(id=uid("cat-fg"), name="Finished Goods", short_code="FG", position=3, created_at=T0),
        dict(id=uid("cat-sub"), name="Sub-Assembly", short_code="SUB", position=4, created_at=T0),
    ]
    subs = [
        ("metal", "Metal", "MT", "cat-rm"),
        ("electrical", "Electrical", "EL", "cat-bo"),
        ("mechanical", "Mechanical", "MC", "cat-bo"),
        ("consumable", "Consumable", "CN", "cat-bo"),
        ("automation", "Industrial Automation", "IA", "cat-fg"),
    ]
    rows["inv_sub_categories"] = [
        dict(id=uid(f"sub-{k}"), name=n, short_code=c, category_id=uid(cat), position=i,
             created_at=T0)
        for i, (k, n, c, cat) in enumerate(subs, 1)
    ]
    rows["inv_sub_categories_2"] = [
        dict(id=uid("sub2-nut"), name="Fastener – Nut", short_code="NUT",
             sub_category_id=uid("sub-mechanical"), source_id=None, standard="ISO 4032",
             description=None, naming_convention="{Type} Nut – {Material} – M{Diameter}",
             convention_notes=None, examples=None, position=1, created_at=T0, hsn_code="7318",
             nomenclature_fields=None, nomenclature_version=1, cut_shape=None, cut_formula=None),
    ]
    rows["inv_field_definitions"] = [
        dict(id=uid(f"fd-{n}"), name=n, field_type="text", required=False, options=None,
             position=i, created_at=T0, updated_at=T0)
        for i, n in enumerate(["source", "legacy_product_code", "alias"], 1)
    ]
    rows["inv_locations"] = [
        dict(id=uid("loc-1"), name="132-1", address="D132 Office Warehouse 1", is_active=True,
             created_at=T0),
        dict(id=uid("loc-2"), name="132-2", address="D132 Office Warehouse 2", is_active=True,
             created_at=T0),
        dict(id=uid("loc-3"), name="C-84", address="C-84 warehouse location", is_active=True,
             created_at=T0),
        dict(id=uid("loc-x"), name="Unassigned", address="Auto-created placeholder",
             is_active=False, created_at=T0),
    ]
    rows["inv_issued_to_targets"] = [
        dict(id=uid("tgt-shop"), name="D132 Shop Floor", is_active=True, created_at=T0),
        dict(id=uid("tgt-dispatch"), name="Dispatch team", is_active=True, created_at=T0),
    ]

    items = [
        # key, code, name, category, sub, unit, status
        ("tube", "RM-MT-0001", "MS Tube – 25×40×2mm", "cat-rm", "sub-metal", "kg", "active"),
        ("relay", "BO-EL-0001", "Relay  – 240V, 2 Pole", "cat-bo", "sub-electrical", "pcs",
         "active"),
        ("nut", "BO-MC-0001", "Hex Nut M8 ", "cat-bo", "sub-mechanical", "pcs", "active"),
        ("belt", "BO-CN-0001", "Scotch Brite Belt", "cat-bo", "sub-consumable", "pcs", "active"),
        ("solenoid", "NW-0001", "Electromagnet Solenoid", None, None, "pcs", "active"),
        ("solenoid2", "BO-EL-0002", "Electromagnet Solenoid ", "cat-bo", "sub-electrical", "pcs",
         "active"),
        ("curtain", "FG-IA-0001", "PVC Curtain for High Speed Door", "cat-fg", "sub-automation",
         "pcs", "active"),
        ("plc", "BO-EL-0003", "Mitsubishi PLC FX5U", "cat-bo", "sub-electrical", "pcs", "active"),
        ("sheet", "RM-MT-0002", "SS Sheet 304 1.5mm", "cat-rm", "sub-metal", "kg", "active"),
        ("oil", "BO-CN-0002", "Cutting Oil", "cat-bo", "sub-consumable", "pcs", "active"),
        ("hinge", "BO-MC-0002", "Hinge Set", "cat-bo", "sub-mechanical", "set", "active"),
        ("bracket", "BO-MC-0003", "Old Bracket", "cat-bo", "sub-mechanical", "pcs", "inactive"),
        ("wire", "RM-MT-0003", "Copper Wire 2.5 sq mm", "cat-rm", "sub-metal", "mtr", "active"),
    ]
    rows["inv_items"] = [
        dict(id=uid(f"item-{k}"), item_code=code, name=name,
             category_id=uid(cat) if cat else None, sub_category_id=uid(sub) if sub else None,
             sub_category_2_id=uid("sub2-nut") if k == "nut" else None, status=status, unit=unit,
             hsn_code="7306" if k == "tube" else None, notes=None, specifications=None,
             alt_units=None, is_spare=False)
        for k, code, name, cat, sub, unit, status in items
    ]

    stock = [
        ("tube", "loc-1", 120), ("relay", "loc-1", 0), ("nut", "loc-1", 500), ("belt", "loc-2", 0),
        ("solenoid", "loc-1", 3), ("solenoid2", "loc-2", 0), ("curtain", "loc-3", 2),
        ("plc", "loc-1", 0), ("oil", "loc-2", 10), ("hinge", "loc-1", 2), ("hinge", "loc-3", 2),
        ("bracket", "loc-3", 7), ("wire", "loc-2", 0),
    ]
    rows["inv_current_stock"] = [
        dict(id=uid(f"stock-{k}-{loc}"), item_id=uid(f"item-{k}"), location_id=uid(loc),
             quantity=float(q), min_stock_level=None, max_stock_level=None,
             last_transaction_at=None, updated_at=_ts("2026-08-21"))
        for k, loc, q in stock
    ]

    txns = [
        # key, item, loc, type, qty, ref_type, cost, day, issued_to, transfer_loc
        ("t1", "tube", "loc-1", "inbound", 100, "purchase_order", 85.0, "2026-08-06", None, None),
        ("t2", "relay", "loc-1", "outbound", 5, "warehouse_issue", None, "2026-08-10",
         "tgt-shop", None),
        ("t3", "belt", "loc-2", "outbound", 10, "warehouse_issue", None, "2026-08-12",
         "tgt-dispatch", None),
        ("t4", "nut", "loc-1", "inbound", 500, "purchase_order", 2.5, "2026-07-01", None, None),
        ("t5", "nut", "loc-1", "outbound", 50, "warehouse_issue", None, "2026-08-15", "tgt-shop",
         None),
        ("t6", "hinge", "loc-1", "transfer_out", 2, "transfer", None, "2026-07-30", None, "loc-3"),
        ("t7", "hinge", "loc-3", "transfer_in", 2, "transfer", None, "2026-07-30", None, "loc-1"),
        ("t8", "solenoid2", "loc-2", "outbound", 3, "warehouse_issue", None, "2026-08-18",
         "tgt-shop", None),
        ("t9", "wire", "loc-2", "outbound", 20, "warehouse_issue", None, "2026-08-19",
         "tgt-dispatch", None),
        ("t10", "curtain", "loc-3", "inbound", 2, "unexpected_receipt", None, "2026-08-20", None,
         None),
        ("t11", "plc", "loc-1", "outbound", 1, "warehouse_issue", None, "2026-08-21", "tgt-shop",
         None),
        ("t12", "belt", "loc-2", "inbound", 20, "purchase_order", 35.0, "2026-04-25", None, None),
    ]
    rows["inv_transactions"] = [
        dict(id=uid(f"txn-{k}"), item_id=uid(f"item-{item}"), location_id=uid(loc),
             transaction_type=tt, quantity=float(q), reference_type=ref, reference_id=None,
             transfer_location_id=uid(tl) if tl else None, unit_cost=cost, notes=None,
             created_by=STAFF_A if i % 2 else STAFF_B, created_at=_ts(day), currency="INR",
             issued_to_id=uid(it) if it else None)
        for i, (k, item, loc, tt, q, ref, cost, day, it, tl) in enumerate(txns)
    ]

    vendors = [
        ("zenith", "Zenith Steels Pvt. Ltd.", "New Delhi", "100% Payment Adavcne"),
        ("anand", "Anand Engineering Pvt. Ltd.", "Chennai", "30 Days"),
        ("summit", "Summit Engineering Pvt. Ltd.", "Indore", None),
        ("vanguard", "Vanguard Electricals", "Pune", "10 Days PDC Against Dispatch"),
        ("global", "Global Automation Inc.", "Singapore", "100% Advance"),
        ("granite", "Granite Steels Pvt. Ltd.", "Kolkata", "50% Adv, Bal Against Dispatch"),
    ]
    rows["proc_vendors"] = [
        dict(id=uid(f"vendor-{k}"), name=n, code=None, city=c, payment_terms=t, is_active=True,
             created_by=STAFF_A, created_at=T0, updated_at=T0)
        for k, n, c, t in vendors
    ]

    # po key, number, vendor, status, placed_on, currency, terms, expected delivery, dispatch,
    # lines: (line key, item, qty, unit, price, received, line expected delivery)
    pos = [
        ("p1", "PO-2026-0001", "zenith", "received", "2026-08-01", "INR",
         "100% Payment Against Dispatch", ["2026-08-06"], None,
         [("l1", "tube", 100, "KG", 85, 100, [])]),
        ("p2", "PO-2026-0002", "anand", "partial", "2026-08-05", "INR",
         "10 DAys PDC Against Dispatch", ["2026-08-10"], [],
         [("l2", "nut", 1000, "Nos.", 2.5, 500, []), ("l3", "relay", 10, "Unit", 450, 0, None)]),
        ("p3", "PO-2026-0003", "vanguard", "placed", "2026-08-12", "INR",
         "10 Days PDC Agst Dispatch", ["2026-08-20", "2026-08-25"], [],
         [("l4", "oil", 20, "Ltr", 300, 0, []), ("l5", "hinge", 5, "Set", 1200, 0, [])]),
        ("p4", "PO-2026-0004", "global", "placed", "2026-08-14", "USD", "100% Advance", None,
         None, [("l6", "plc", 2, "Nos", 410, 0, [])]),
        ("p5", "PO-2026-0005", "zenith", "placed", "2026-08-18", "INR", "", [], [],
         [("l7", "tube", 50, "KG", 88, 0, []), ("l8", "wire", 100, "Mtr", 12, 0, [])]),
        ("p6", "PO-2026-0006", "anand", "received", "2026-08-03", "INR", "30 Days Credit",
         ["2026-08-08"], [],
         [("l9", "belt", 20, "pcs", 35, 20, []), ("l10", "solenoid2", 4, "KG", 250, 4, [])]),
        ("p7", "PO-2026-0010", "summit", "placed", "2026-08-19", "INR",
         "50% Advance & 50% Against Dispatch", ["2026-09-18"], [],
         [("l11", "curtain", 1, "pcs", 18000, 0, [])]),
    ]
    rows["proc_purchase_orders"], rows["proc_po_lines"] = [], []
    for key, number, vendor, status, placed, cur, terms, edd, disp, lines in pos:
        subtotal = sum(Decimal(str(q)) * Decimal(str(p)) for _, _, q, _, p, _, _ in lines)
        created = _ts(placed)
        rows["proc_purchase_orders"].append(dict(
            id=uid(f"po-{key}"), po_number=number, vendor_id=uid(f"vendor-{vendor}"),
            status=status, placed_on=date.fromisoformat(placed), currency=cur, subtotal=subtotal,
            tax_amount=Decimal("0"), total_amount=subtotal, payment_terms=terms,
            delivery_location_id=None, ship_to_address=None, custom_fields="{}",
            created_by=STAFF_A, created_at=created, updated_at=created,
            expected_delivery_date=_dates(edd), expected_dispatch_date=_dates(disp)))
        for pos_i, (lk, item, q, unit, price, recv, ledd) in enumerate(lines, 1):
            line_total = Decimal(str(q)) * Decimal(str(price))
            rows["proc_po_lines"].append(dict(
                id=uid(f"line-{lk}"), po_id=uid(f"po-{key}"), inv_item_id=uid(f"item-{item}"),
                quantity_ordered=Decimal(str(q)), quantity_received=Decimal(str(recv)), unit=unit,
                unit_price=Decimal(str(price)), tax_percentage=Decimal("0"),
                line_subtotal=line_total, line_tax=Decimal("0"), line_total=line_total,
                notes=None, position=pos_i, custom_fields="{}", created_at=created,
                updated_at=created, is_regularised=False, expected_delivery_date=_dates(ledd),
                expected_dispatch_date="[]"))

    tranches = [
        # key, po, seq, stage, pct, advance, blocks, basis, offset, cleared
        ("tr1", "p1", 0, "100% Payment Against Dispatch", 100, False, True, "dispatch", 0,
         "2026-08-07"),
        ("tr2", "p2", 0, "10 Days PDC Agst Dispatch", 100, False, True, "dispatch", 10, None),
        ("tr3", "p3", 0, "10 DAys PDC Against Dispatch", 100, False, True, "dispatch", 10, None),
        ("tr4", "p4", 0, "Advance", 100, True, True, "advance", 0, None),
        ("tr5", "p7", 0, "Advance", 50, True, False, "advance", 0, None),
        ("tr6", "p7", 1, "Balance Against Dispatch", 50, False, True, "dispatch", 0, None),
    ]
    rows["proc_po_payment_tranches"] = [
        dict(id=uid(f"tranche-{k}"), po_id=uid(f"po-{po}"), sequence=seq, stage=stage,
             percentage=Decimal(pct), amount=None, is_advance=adv, blocks_dispatch=blocks,
             due_basis=basis, due_offset_days=off, source="extraction",
             cleared_at=_ts(cl) if cl else None, cleared_by=STAFF_B if cl else None,
             created_at=T0, updated_at=T0)
        for k, po, seq, stage, pct, adv, blocks, basis, off, cl in tranches
    ]

    rows["proc_po_receipts"] = [
        dict(id=uid("rcpt-1"), po_line_id=uid("line-l1"), quantity=Decimal(100),
             location_id=uid("loc-1"), notes=None, inv_transaction_id=uid("txn-t1"),
             received_by=STAFF_B, received_at=_ts("2026-08-06")),
        dict(id=uid("rcpt-2"), po_line_id=uid("line-l2"), quantity=Decimal(500),
             location_id=uid("loc-1"), notes="Call vendor on +91 98765 43210 for balance",
             inv_transaction_id=None, received_by=STAFF_B, received_at=_ts("2026-08-12")),
        dict(id=uid("rcpt-3"), po_line_id=uid("line-l9"), quantity=Decimal(20),
             location_id=uid("loc-2"), notes=None, inv_transaction_id=None, received_by=STAFF_A,
             received_at=_ts("2026-08-07")),
        dict(id=uid("rcpt-4"), po_line_id=uid("line-l10"), quantity=Decimal(4),
             location_id=uid("loc-2"), notes=None, inv_transaction_id=None, received_by=STAFF_A,
             received_at=_ts("2026-08-09")),
    ]
    rows["proc_po_line_regularisations"] = [
        dict(id=uid("reg-1"), po_id=uid("po-p2"), po_line_id=uid("line-l2"),
             ordered_qty=Decimal(1000), received_qty_before=Decimal(500),
             regularised_qty=Decimal(0), received_qty_after=Decimal(500),
             qty_variance=Decimal(-500), unit_price=Decimal("2.5"), actual_amount=Decimal(1250),
             expected_amount=Decimal(2500), amount_variance=Decimal(-1250),
             notes="Short supply", inv_transaction_id=None, regularised_by=STAFF_B,
             regularised_at=_ts("2026-08-16"), reviewed_by=None, reviewed_at=None,
             review_notes=None),
    ]
    rows["proc_unexpected_receipt_headers"] = [
        dict(id=uid("urh-1"), received_by=STAFF_B, received_at=_ts("2026-08-20"),
             notes="Arrived without PO", vendor_name="Zenith Steels Pvt. Ltd."),
        dict(id=uid("urh-2"), received_by=STAFF_A, received_at=_ts("2026-08-21"), notes=None,
             vendor_name="Anand Engineering Pvt. Ltd."),
    ]
    rows["proc_unexpected_receipts"] = [
        dict(id=uid("ur-1"), inv_item_id=uid("item-curtain"), quantity=Decimal(2),
             location_id=uid("loc-3"), notes=None, inv_transaction_id=uid("txn-t10"),
             received_by=STAFF_B, received_at=_ts("2026-08-20"), resolved_po_id=None,
             resolved_by=None, resolved_at=None, header_id=uid("urh-1")),
        dict(id=uid("ur-2"), inv_item_id=uid("item-solenoid"), quantity=Decimal(1),
             location_id=uid("loc-1"), notes=None, inv_transaction_id=None, received_by=STAFF_B,
             received_at=_ts("2026-08-20"), resolved_po_id=uid("po-p7"), resolved_by=STAFF_A,
             resolved_at=_ts("2026-08-21"), header_id=uid("urh-1")),
        dict(id=uid("ur-3"), inv_item_id=uid("item-belt"), quantity=Decimal(5),
             location_id=uid("loc-2"), notes=None, inv_transaction_id=None, received_by=STAFF_A,
             received_at=_ts("2026-08-21"), resolved_po_id=None, resolved_by=None,
             resolved_at=None, header_id=uid("urh-2")),
    ]
    return rows


# Insert order respects foreign keys.
TABLE_ORDER = [
    "inv_categories", "inv_sub_categories", "inv_sub_categories_2", "inv_field_definitions",
    "inv_locations", "inv_issued_to_targets", "inv_items", "inv_current_stock",
    "inv_transactions", "proc_vendors", "proc_purchase_orders", "proc_po_lines",
    "proc_po_payment_tranches", "proc_po_receipts", "proc_po_line_regularisations",
    "proc_unexpected_receipt_headers", "proc_unexpected_receipts",
]
