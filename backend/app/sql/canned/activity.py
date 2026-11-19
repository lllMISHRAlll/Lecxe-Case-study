"""Latest dates that have data, used to explain empty date-filtered results."""

from __future__ import annotations

from datetime import date, datetime

from app.sql.executor import QueryExecutor

LATEST_SQL = """
SELECT (SELECT MAX(placed_on) FROM proc_purchase_orders) AS po_placed,
       (SELECT MAX(created_at) FROM inv_transactions) AS stock_movement
"""


def latest_activity(executor: QueryExecutor) -> dict[str, date | None]:
    record = executor.run(LATEST_SQL).records()[0]
    return {k: (v.date() if isinstance(v, datetime) else v) for k, v in record.items()}
