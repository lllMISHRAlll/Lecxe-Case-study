"""Business Owner buttons."""

from app.auth.roles import Role
from app.sql.canned.base import CannedQuery, ChartHint, inr

BO = frozenset({Role.BUSINESS_OWNER})

QUERIES = [
    CannedQuery(
        id="bo_top_vendors", label="Top vendors by spend",
        description="The ten vendors with the highest PO value, in INR.", roles=BO,
        chart=ChartHint("horizontal_bar", "vendor", ("spend_inr",)),
        sql=f"""
SELECT v.name AS vendor, COUNT(p.id) AS pos, ROUND(SUM({inr('p.total_amount')}), 2) AS spend_inr
FROM proc_purchase_orders p
JOIN proc_vendors v ON v.id = p.vendor_id
GROUP BY v.name
ORDER BY spend_inr DESC
LIMIT 10"""),
    CannedQuery(
        id="bo_spend_by_category", label="Spend by category",
        description="PO line value per item category, in INR.", roles=BO,
        chart=ChartHint("pie", "category", ("spend_inr",)),
        sql=f"""
SELECT COALESCE(c.name, 'Uncategorised') AS category,
       ROUND(SUM({inr('l.line_total')}), 2) AS spend_inr
FROM proc_po_lines l
JOIN proc_purchase_orders p ON p.id = l.po_id
LEFT JOIN inv_items i ON i.id = l.inv_item_id
LEFT JOIN inv_categories c ON c.id = i.category_id
GROUP BY COALESCE(c.name, 'Uncategorised')
ORDER BY spend_inr DESC
LIMIT 500"""),
    CannedQuery(
        id="bo_po_pipeline", label="PO pipeline",
        description="Number and value of POs by receiving status.", roles=BO,
        chart=ChartHint("bar", "status", ("value_inr",)),
        sql=f"""
SELECT p.status, COUNT(*) AS pos, ROUND(SUM({inr('p.total_amount')}), 2) AS value_inr
FROM proc_purchase_orders p
GROUP BY p.status
ORDER BY CASE p.status WHEN 'placed' THEN 1 WHEN 'partial' THEN 2 ELSE 3 END
LIMIT 10"""),
    CannedQuery(
        id="bo_vendor_scorecard", label="Vendor scorecard",
        description="Spend, POs, fulfilment and on-time receipts per vendor.", roles=BO,
        sql=f"""
WITH spend AS (
  SELECT p.vendor_id, COUNT(*) AS pos, SUM({inr('p.total_amount')}) AS spend_inr
  FROM proc_purchase_orders p
  GROUP BY p.vendor_id
), qty AS (
  SELECT p.vendor_id, SUM(l.quantity_ordered) AS ordered, SUM(l.quantity_received) AS received
  FROM proc_po_lines l
  JOIN proc_purchase_orders p ON p.id = l.po_id
  GROUP BY p.vendor_id
), receipts AS (
  SELECT p.vendor_id, COUNT(*) AS receipts,
         SUM(CASE WHEN r.received_at::date <= (p.expected_delivery_date ->> 0)::date
                  THEN 1 ELSE 0 END) AS on_time
  FROM proc_po_receipts r
  JOIN proc_po_lines l ON l.id = r.po_line_id
  JOIN proc_purchase_orders p ON p.id = l.po_id
  WHERE json_array_length(p.expected_delivery_date) > 0
  GROUP BY p.vendor_id
)
SELECT v.name AS vendor, s.pos, ROUND(s.spend_inr, 2) AS spend_inr,
       ROUND(100.0 * q.received / NULLIF(q.ordered, 0), 1) AS fulfilment_pct,
       ROUND(100.0 * rc.on_time / NULLIF(rc.receipts, 0), 1) AS on_time_pct
FROM proc_vendors v
JOIN spend s ON s.vendor_id = v.id
LEFT JOIN qty q ON q.vendor_id = v.id
LEFT JOIN receipts rc ON rc.vendor_id = v.id
ORDER BY s.spend_inr DESC
LIMIT 500"""),
    CannedQuery(
        id="bo_stock_in_out_weekly", label="Stock in vs out",
        description="Inbound and outbound quantity by week.", roles=BO,
        chart=ChartHint("line", "week", ("qty_in", "qty_out")),
        sql="""
SELECT date_trunc('week', t.created_at)::date AS week,
       SUM(CASE WHEN t.transaction_type = 'inbound' THEN t.quantity ELSE 0 END) AS qty_in,
       SUM(CASE WHEN t.transaction_type = 'outbound' THEN t.quantity ELSE 0 END) AS qty_out
FROM inv_transactions t
WHERE t.transaction_type IN ('inbound', 'outbound')
GROUP BY date_trunc('week', t.created_at)::date
ORDER BY week
LIMIT 500"""),
    CannedQuery(
        id="bo_unplanned_by_vendor", label="Unplanned deliveries",
        description="Deliveries without a PO, per vendor.", roles=BO,
        chart=ChartHint("bar", "vendor", ("receipts",)),
        sql="""
SELECT COALESCE(h.vendor_name, 'Unknown vendor') AS vendor, COUNT(*) AS receipts,
       SUM(CASE WHEN r.resolved_po_id IS NULL THEN 1 ELSE 0 END) AS unresolved
FROM proc_unexpected_receipts r
LEFT JOIN proc_unexpected_receipt_headers h ON h.id = r.header_id
GROUP BY COALESCE(h.vendor_name, 'Unknown vendor')
ORDER BY receipts DESC, vendor
LIMIT 500"""),
]
