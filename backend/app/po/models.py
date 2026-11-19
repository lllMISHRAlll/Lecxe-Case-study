"""Purchase order draft models. Money and quantities are Decimal end to end."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from app.po.rules import Review


class VendorRef(BaseModel):
    id: str
    name: str
    payment_terms: str | None = None
    is_active: bool = True


class ItemRef(BaseModel):
    id: str
    code: str
    name: str
    unit: str
    is_active: bool = True


class LocationRef(BaseModel):
    id: str
    name: str


class POLine(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    position: int
    item: ItemRef | None = None
    quantity: Decimal | None = Field(default=None, gt=0)
    unit: str | None = None
    unit_price: Decimal | None = Field(default=None, gt=0)
    tax_percentage: Decimal = Field(default=Decimal(0), ge=0, le=100)
    suggested_price: Decimal | None = None


class PODraft(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    status: Literal["open", "confirmed", "cancelled"] = "open"
    idempotency_key: str
    vendor: VendorRef | None = None
    currency: Literal["INR", "USD"] = "INR"
    payment_terms: str | None = None
    placed_on: date | None = None
    delivery_location: LocationRef | None = None
    expected_delivery_date: date | None = None
    lines: list[POLine] = Field(default_factory=list)
    defaults_used: list[str] = Field(default_factory=list)
    created_po_number: str | None = None
    created_po_id: str | None = None
    pending: dict[str, Any] | None = None  # choice waiting for the user, e.g. which vendor
    last_question: str | None = None  # what the assistant asked last, for the extractor

    def to_contract(self, review: Review) -> dict[str, Any]:
        from app.po.totals import draft_totals, line_totals

        totals = draft_totals(self.lines)
        return {
            "status": self.status,
            "idempotency_key": self.idempotency_key,
            "vendor": {"id": self.vendor.id, "name": self.vendor.name} if self.vendor else None,
            "currency": self.currency,
            "payment_terms": self.payment_terms,
            "placed_on": self.placed_on.isoformat() if self.placed_on else None,
            "delivery_location": (self.delivery_location.model_dump()
                                  if self.delivery_location else None),
            "expected_delivery_date": (self.expected_delivery_date.isoformat()
                                       if self.expected_delivery_date else None),
            "lines": [
                {
                    "position": line.position,
                    "item": ({"id": line.item.id, "code": line.item.code,
                              "name": line.item.name, "unit": line.item.unit}
                             if line.item else None),
                    "quantity": fmt_qty(line.quantity),
                    "unit": line.unit,
                    "unit_price": fmt_money(line.unit_price),
                    "tax_percentage": fmt_qty(line.tax_percentage),
                    "line_total": fmt_money(line_totals(line).total),
                    "warnings": review.line_warnings.get(line.position, []),
                }
                for line in self.lines
            ],
            "subtotal": fmt_money(totals.subtotal),
            "tax_amount": fmt_money(totals.tax),
            "total_amount": fmt_money(totals.total),
            "missing": review.missing,
            "warnings": [*review.errors, *review.defaults_used],
            "po_number": self.created_po_number,
        }


def fmt_money(value: Decimal | None) -> str | None:
    return None if value is None else f"{value.quantize(Decimal('0.01')):f}"


def fmt_qty(value: Decimal | None) -> str | None:
    if value is None:
        return None
    text = f"{value.normalize():f}"
    return text
