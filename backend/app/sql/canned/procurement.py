"""Procurement Manager buttons."""

from app.auth.roles import Role
from app.sql.canned.base import CannedQuery, ChartHint, inr

PM = frozenset({Role.PROCUREMENT_MANAGER})

QUERIES = [
    CannedQuery(
        id="pm_open_pos", label="Open POs",
        description="POs not yet fully received, with value and age.", roles=PM,
        sql="""
SELECT p.po_number, v.name AS vendor, p.status, p.placed_on, p.currency, p.total_amount,
       CAST(:today AS date) - p.placed_on AS age_days
FROM proc_purchase_orders p
JOIN proc_vendors v ON v.id = p.vendor_id
WHERE p.status IN ('placed', 'partial')
ORDER BY p.placed_on, p.po_number
LIMIT 500"""),
    CannedQuery(
        id="pm_overdue", label="Overdue deliveries",
        description="Open POs whose expected delivery date has passed.", roles=PM,
        sql="""
WITH open_po AS (
  SELECT p.id, p.po_number, p.vendor_id, p.status,
         (p.expected_delivery_date ->> 0)::date AS expected_on
  FROM proc_purchase_orders p
  WHERE p.status IN ('placed', 'partial') AND json_array_length(p.expected_delivery_date) > 0
)
SELECT o.po_number, v.name AS vendor, o.status, o.expected_on,
       CAST(:today AS date) - o.expected_on AS days_late,
       SUM(l.quantity_ordered - l.quantity_received) AS pending_qty
FROM open_po o
JOIN proc_vendors v ON v.id = o.vendor_id
JOIN proc_po_lines l ON l.po_id = o.id
WHERE o.expected_on < CAST(:today AS date)
GROUP BY o.po_number, v.name, o.status, o.expected_on
ORDER BY days_late DESC, o.po_number
LIMIT 500"""),
    CannedQuery(
        id="pm_out_of_stock_in_use", label="Out of stock, in use",
        description="Items at zero stock that have been issued, with the last vendor and price.",
        roles=PM,
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
), last_buy AS (
  SELECT l.inv_item_id, v.name AS vendor, l.unit_price, p.currency,
         ROW_NUMBER() OVER (PARTITION BY l.inv_item_id
                            ORDER BY p.placed_on DESC, p.po_number DESC) AS rn
  FROM proc_po_lines l
  JOIN proc_purchase_orders p ON p.id = l.po_id
  JOIN proc_vendors v ON v.id = p.vendor_id
)
SELECT st.item_code, st.name AS item, st.unit, u.issued_qty, u.last_issued::date AS last_issued,
       lb.vendor AS last_vendor, lb.unit_price AS last_price, lb.currency
FROM stock st
JOIN used u ON u.item_id = st.id
LEFT JOIN last_buy lb ON lb.inv_item_id = st.id AND lb.rn = 1
WHERE st.on_hand <= 0
ORDER BY u.last_issued DESC, st.item_code
LIMIT 500"""),
    CannedQuery(
        id="pm_spend_by_vendor", label="Spend by vendor",
        description="Total PO value per vendor in INR.", roles=PM,
        chart=ChartHint("horizontal_bar", "vendor", ("spend_inr",)),
        sql=f"""
SELECT v.name AS vendor, COUNT(p.id) AS pos, ROUND(SUM({inr('p.total_amount')}), 2) AS spend_inr
FROM proc_purchase_orders p
JOIN proc_vendors v ON v.id = p.vendor_id
GROUP BY v.name
ORDER BY spend_inr DESC
LIMIT 500"""),
    CannedQuery(
        id="pm_fulfilment", label="Vendor fulfilment",
        description="Received vs ordered quantity per vendor. Lines in a different unit from "
                    "the item are counted separately.", roles=PM,
        chart=ChartHint("bar", "vendor", ("fulfilment_pct",)),
        sql="""
SELECT v.name AS vendor, SUM(l.quantity_ordered) AS ordered_qty,
       SUM(l.quantity_received) AS received_qty,
       ROUND(100.0 * SUM(l.quantity_received) / NULLIF(SUM(l.quantity_ordered), 0), 1)
         AS fulfilment_pct,
       SUM(CASE WHEN l.unit IS DISTINCT FROM i.unit THEN 1 ELSE 0 END) AS unit_mismatch_lines
FROM proc_po_lines l
JOIN proc_purchase_orders p ON p.id = l.po_id
JOIN proc_vendors v ON v.id = p.vendor_id
LEFT JOIN inv_items i ON i.id = l.inv_item_id
GROUP BY v.name
ORDER BY fulfilment_pct, v.name
LIMIT 500"""),
    CannedQuery(
        id="pm_unexpected_receipts", label="Unexpected receipts",
        description="Deliveries that arrived without a PO and still need reconciling.",
        roles=PM,
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
        id="pm_blocking_payments", label="Payments blocking dispatch",
        description="Unpaid instalments that stop vendors from dispatching.", roles=PM,
        sql="""
SELECT p.po_number, v.name AS vendor, t.stage, t.percentage,
       ROUND(p.total_amount * t.percentage / 100, 2) AS amount, p.currency, p.status
FROM proc_po_payment_tranches t
JOIN proc_purchase_orders p ON p.id = t.po_id
JOIN proc_vendors v ON v.id = p.vendor_id
WHERE t.blocks_dispatch AND t.cleared_at IS NULL AND p.status <> 'received'
ORDER BY p.placed_on, p.po_number, t.sequence
LIMIT 500"""),
]
