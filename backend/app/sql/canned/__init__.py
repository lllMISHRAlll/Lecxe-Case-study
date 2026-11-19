"""All query buttons, by role."""

from app.sql.canned import owner, procurement, warehouse
from app.sql.canned.activity import latest_activity
from app.sql.canned.base import CannedContext, CannedQuery, ChartHint, Registry

REGISTRY = Registry()
REGISTRY.register(procurement.QUERIES)
REGISTRY.register(owner.QUERIES)
REGISTRY.register(warehouse.QUERIES)

__all__ = ["REGISTRY", "CannedContext", "CannedQuery", "ChartHint", "latest_activity"]
