"""What the PO flow needs to know about vendors, items, locations and past prices."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Protocol

from app.po.models import ItemRef, LocationRef, VendorRef


@dataclass(frozen=True)
class PriceRecord:
    item_id: str
    vendor_id: str
    currency: str
    unit_price: Decimal
    placed_on: date


class Catalog(Protocol):
    @property
    def vendors(self) -> list[VendorRef]: ...

    @property
    def items(self) -> list[ItemRef]: ...

    @property
    def locations(self) -> list[LocationRef]: ...

    def last_price(self, item_id: str, vendor_id: str | None, currency: str) -> Decimal | None:
        ...

    def recent_vendors(self, limit: int) -> list[VendorRef]: ...


@dataclass
class InMemoryCatalog:
    vendors: list[VendorRef] = field(default_factory=list)
    items: list[ItemRef] = field(default_factory=list)
    locations: list[LocationRef] = field(default_factory=list)
    prices: list[PriceRecord] = field(default_factory=list)

    def last_price(self, item_id: str, vendor_id: str | None, currency: str) -> Decimal | None:
        return best_price(self.prices, item_id, vendor_id, currency)

    def recent_vendors(self, limit: int) -> list[VendorRef]:
        return recent_vendors(self.vendors, self.prices, limit)


def recent_vendors(vendors: list[VendorRef], prices: list[PriceRecord],
                   limit: int) -> list[VendorRef]:
    """Active vendors, most recently ordered from first, then the rest by name."""
    active = {v.id: v for v in vendors if v.is_active}
    ordered: list[VendorRef] = []
    for price in sorted(prices, key=lambda p: p.placed_on, reverse=True):
        vendor = active.get(price.vendor_id)
        if vendor and vendor not in ordered:
            ordered.append(vendor)
    ordered += [v for v in sorted(active.values(), key=lambda v: v.name) if v not in ordered]
    return ordered[:limit]


def best_price(prices: list[PriceRecord], item_id: str, vendor_id: str | None,
               currency: str) -> Decimal | None:
    """Latest price for the item in this currency, preferring the same vendor."""
    same_currency = [p for p in prices if p.item_id == item_id and p.currency == currency]
    same_vendor = [p for p in same_currency if p.vendor_id == vendor_id]
    pool = same_vendor or same_currency
    if not pool:
        return None
    return max(pool, key=lambda p: p.placed_on).unit_price
