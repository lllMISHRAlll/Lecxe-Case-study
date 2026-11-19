from decimal import Decimal

from app.po.catalog_db import DbCatalog
from tests.fixtures.ids import uid


def test_loads_vendors_items_and_active_locations(db):
    cat = DbCatalog.load(db.read_engine)
    assert len(cat.vendors) == 6
    assert len(cat.items) == 13
    assert {loc.name for loc in cat.locations} == {"132-1", "132-2", "C-84"}
    bracket = next(i for i in cat.items if i.code == "BO-MC-0003")
    assert bracket.is_active is False
    summit = next(v for v in cat.vendors if v.name.startswith("Summit"))
    assert summit.payment_terms is None


def test_last_price_from_po_history(db):
    cat = DbCatalog.load(db.read_engine)
    assert cat.last_price(uid("item-tube"), uid("vendor-zenith"), "INR") == Decimal("88")
    assert cat.last_price(uid("item-plc"), uid("vendor-zenith"), "INR") is None
    assert cat.last_price(uid("item-plc"), uid("vendor-global"), "USD") == Decimal("410")
