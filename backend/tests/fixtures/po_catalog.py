"""In-memory catalog for PO unit tests, mirroring the normalised seed."""

from datetime import date
from decimal import Decimal

from app.po.catalog import InMemoryCatalog, PriceRecord
from app.po.models import ItemRef, LocationRef, VendorRef


def catalog() -> InMemoryCatalog:
    return InMemoryCatalog(
        vendors=[
            VendorRef(id="v-zenith", name="Zenith Steels Pvt. Ltd.", payment_terms="100% Advance"),
            VendorRef(id="v-anand", name="Anand Engineering Pvt. Ltd.",
                      payment_terms="30 Days Credit"),
            VendorRef(id="v-summit", name="Summit Engineering Pvt. Ltd.", payment_terms=None),
            VendorRef(id="v-zen2", name="Zenith Automation", payment_terms="30 Days Credit"),
            VendorRef(id="v-old", name="Old Traders", payment_terms=None, is_active=False),
        ],
        items=[
            ItemRef(id="i-tube", code="RM-MT-0001", name="MS Tube – 25×40×2mm", unit="kg"),
            ItemRef(id="i-nut", code="BO-MC-0001", name="Hex Nut M8", unit="pcs"),
            ItemRef(id="i-nut10", code="BO-MC-0004", name="Hex Nut M10", unit="pcs"),
            ItemRef(id="i-relay", code="BO-EL-0001", name="Relay – 240V, 2 Pole", unit="pcs"),
            ItemRef(id="i-hinge", code="BO-MC-0002", name="Hinge Set", unit="set"),
            ItemRef(id="i-old", code="BO-MC-0003", name="Old Bracket", unit="pcs",
                    is_active=False),
        ],
        locations=[LocationRef(id="l-1", name="132-1"), LocationRef(id="l-3", name="C-84")],
        prices=[
            PriceRecord("i-tube", "v-zenith", "INR", Decimal("88"), date(2026, 8, 18)),
            PriceRecord("i-tube", "v-anand", "INR", Decimal("80"), date(2026, 8, 20)),
            PriceRecord("i-relay", "v-anand", "INR", Decimal("450"), date(2026, 8, 5)),
            PriceRecord("i-relay", "v-zenith", "USD", Decimal("6"), date(2026, 8, 25)),
        ],
    )
