"""Catalog loaded from the company tables (read-only)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import Engine, text

from app.po.catalog import PriceRecord, best_price
from app.po.models import ItemRef, LocationRef, VendorRef


@dataclass
class DbCatalog:
    vendors: list[VendorRef]
    items: list[ItemRef]
    locations: list[LocationRef]
    prices: list[PriceRecord]

    @classmethod
    def load(cls, engine: Engine) -> DbCatalog:
        with engine.connect() as conn:
            vendors = [VendorRef(id=r.id, name=r.name, payment_terms=r.payment_terms,
                                 is_active=r.is_active)
                       for r in conn.execute(text(
                           "SELECT id, name, payment_terms, is_active FROM proc_vendors "
                           "ORDER BY name"))]
            items = [ItemRef(id=r.id, code=r.item_code, name=r.name, unit=r.unit,
                             is_active=r.status == "active")
                     for r in conn.execute(text(
                         "SELECT id, item_code, name, unit, status FROM inv_items "
                         "ORDER BY item_code"))]
            locations = [LocationRef(id=r.id, name=r.name) for r in conn.execute(text(
                "SELECT id, name FROM inv_locations WHERE is_active ORDER BY name"))]
            prices = [PriceRecord(r.inv_item_id, r.vendor_id, r.currency, r.unit_price,
                                  r.placed_on)
                      for r in conn.execute(text(
                          "SELECT l.inv_item_id, p.vendor_id, p.currency, l.unit_price, "
                          "p.placed_on FROM proc_po_lines l "
                          "JOIN proc_purchase_orders p ON p.id = l.po_id "
                          "WHERE p.placed_on IS NOT NULL"))]
        return cls(vendors, items, locations, prices)

    def last_price(self, item_id: str, vendor_id: str | None, currency: str) -> Decimal | None:
        return best_price(self.prices, item_id, vendor_id, currency)
