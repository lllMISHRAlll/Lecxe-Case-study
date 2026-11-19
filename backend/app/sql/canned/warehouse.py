"""Warehouse Manager buttons."""

from app.auth.roles import Role
from app.sql.canned.base import CannedQuery, ChartHint

WM = frozenset({Role.WAREHOUSE_MANAGER})

QUERIES = [
    CannedQuery(
        id="wm_stock_by_warehouse", label="Stock by warehouse",
        description="Items in stock and out of stock at each active warehouse.", roles=WM,
        chart=ChartHint("bar", "warehouse", ("items_in_stock", "items_out_of_stock")),
        sql="""
SELECT loc.name AS warehouse,
       SUM(CASE WHEN s.quantity > 0 THEN 1 ELSE 0 END) AS items_in_stock,
       SUM(CASE WHEN s.quantity <= 0 THEN 1 ELSE 0 END) AS items_out_of_stock
FROM inv_current_stock s
JOIN inv_locations loc ON loc.id = s.location_id
WHERE loc.is_active
GROUP BY loc.name
ORDER BY items_in_stock DESC, warehouse
LIMIT 500"""),
    CannedQuery(
        id="wm_out_of_stock_in_use", label="Out of stock, in use",
        description="Items at zero stock that have been issued.", roles=WM,
        sql="""
WITH stock AS (
  SELECT i.id, i.item_code, i.name, i.unit, COALESCE(SUM(s.quantity), 0) AS on_hand
  FROM inv_items i
  LEFT JOIN inv_current_stock s ON s.item_id = i.id
  WHERE i.status = 'active'
  GROUP BY i.id, i.item_code, i.name, i.unit
), used AS (
  SELECT t.item_id, MAX(t.created_at) AS last_issued, SUM(t.quantity) AS issued_qty
  FROM inv_transactions t
  WHERE t.transaction_type = 'outbound'
  GROUP BY t.item_id
)
SELECT st.item_code, st.name AS item, st.unit, u.issued_qty, u.last_issued::date AS last_issued
FROM stock st
JOIN used u ON u.item_id = st.id
WHERE st.on_hand <= 0
ORDER BY u.last_issued DESC, st.item_code
LIMIT 500"""),
    CannedQuery(
        id="wm_expected_inbound", label="Expected inbound",
        description="Open PO lines still to arrive, with expected dates.", roles=WM,
        sql="""
SELECT p.po_number, v.name AS vendor, i.item_code, i.name AS item,
       l.quantity_ordered - l.quantity_received AS pending_qty, l.unit,
       (p.expected_delivery_date ->> 0)::date AS expected_on, l.line_total, p.currency
FROM proc_po_lines l
JOIN proc_purchase_orders p ON p.id = l.po_id
JOIN proc_vendors v ON v.id = p.vendor_id
LEFT JOIN inv_items i ON i.id = l.inv_item_id
WHERE p.status IN ('placed', 'partial') AND l.quantity_received < l.quantity_ordered
ORDER BY expected_on, p.po_number, l.position
LIMIT 500"""),
    CannedQuery(
        id="wm_recent_movements", label="Recent movements",
        description="The latest 50 stock movements.", roles=WM,
        sql="""
SELECT t.created_at AS moved_at, i.item_code, i.name AS item, t.transaction_type, t.quantity,
       i.unit, loc.name AS location, tg.name AS issued_to
FROM inv_transactions t
LEFT JOIN inv_items i ON i.id = t.item_id
LEFT JOIN inv_locations loc ON loc.id = t.location_id
LEFT JOIN inv_issued_to_targets tg ON tg.id = t.issued_to_id
ORDER BY t.created_at DESC, t.id
LIMIT 50"""),
    CannedQuery(
        id="wm_consumption_by_target", label="Consumption by target",
        description="Stock issued to each shop floor or team.", roles=WM,
        chart=ChartHint("bar", "issued_to", ("issues",)),
        sql="""
SELECT COALESCE(tg.name, 'Not recorded') AS issued_to, COUNT(*) AS issues, SUM(t.quantity) AS qty
FROM inv_transactions t
LEFT JOIN inv_issued_to_targets tg ON tg.id = t.issued_to_id
WHERE t.transaction_type = 'outbound'
GROUP BY COALESCE(tg.name, 'Not recorded')
ORDER BY issues DESC, issued_to
LIMIT 500"""),
    CannedQuery(
        id="wm_unexpected_receipts", label="Unexpected receipts",
        description="Deliveries that arrived without a PO and still need reconciling.",
        roles=WM,
        sql="""
SELECT h.vendor_name AS vendor, i.item_code, i.name AS item, r.quantity, i.unit,
       r.received_at::date AS received_on, loc.name AS location
FROM proc_unexpected_receipts r
JOIN inv_items i ON i.id = r.inv_item_id
LEFT JOIN proc_unexpected_receipt_headers h ON h.id = r.header_id
LEFT JOIN inv_locations loc ON loc.id = r.location_id
WHERE r.resolved_po_id IS NULL
ORDER BY r.received_at, i.item_code
LIMIT 500"""),
    CannedQuery(
        id="wm_no_movement", label="No movement on record",
        description="Active items that have never moved in or out.", roles=WM,
        sql="""
SELECT i.item_code, i.name AS item, COALESCE(c.name, 'Uncategorised') AS category, i.unit,
       COALESCE(SUM(s.quantity), 0) AS on_hand
FROM inv_items i
LEFT JOIN inv_categories c ON c.id = i.category_id
LEFT JOIN inv_current_stock s ON s.item_id = i.id
WHERE i.status = 'active'
  AND NOT EXISTS (SELECT 1 FROM inv_transactions t WHERE t.item_id = i.id)
GROUP BY i.item_code, i.name, c.name, i.unit
ORDER BY on_hand DESC, i.item_code
LIMIT 500"""),
]
