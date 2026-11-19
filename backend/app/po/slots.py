"""Turns details the LLM extracted from a message into changes on the draft."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from app.domain.vocabulary import canonical_unit
from app.po.catalog import Catalog
from app.po.models import PODraft, POLine
from app.po.resolver import EntityResolver
from app.po.rules import Option


class ExtractedLine(BaseModel):
    action: Literal["add", "update", "remove"] = "add"
    line: int | None = Field(default=None, description="Line number for update or remove")
    apply_to: Literal["line", "all"] = Field(
        default="line", description="'all' updates every existing line (optionally only those "
                                    "in for_unit)")
    for_unit: str | None = Field(default=None, description="With apply_to='all': only lines in "
                                                           "this unit, e.g. pcs or kg")
    item: str | None = Field(default=None, description="Item code or name as the user wrote it")
    quantity: float | None = None
    unit: str | None = None
    unit_price: float | None = None
    tax_percentage: float | None = None


class SlotExtraction(BaseModel):
    vendor: str | None = None
    lines: list[ExtractedLine] = Field(default_factory=list)
    currency: Literal["INR", "USD"] | None = None
    payment_terms: str | None = None
    placed_on: date | None = None
    expected_delivery_date: date | None = None
    delivery_location: str | None = None


class Unresolved(BaseModel):
    kind: Literal["vendor", "item", "location", "invalid"]
    query: str
    choices: list[Option] = Field(default_factory=list)
    pending: dict[str, str] = Field(default_factory=dict)


def _dec(value: float | None) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def _renumber(draft: PODraft) -> None:
    for i, line in enumerate(draft.lines, 1):
        line.position = i


def _set_fields(line: POLine, extracted: ExtractedLine, problems: list[Unresolved]) -> None:
    for field_name in ("quantity", "unit_price", "tax_percentage"):
        value = _dec(getattr(extracted, field_name))
        if value is None:
            continue
        try:
            setattr(line, field_name, value)
        except ValidationError:
            label = field_name.replace("_", " ")
            problems.append(Unresolved(kind="invalid", query=f"The {label} must be more than "
                                                             "zero."))
    if extracted.unit:
        line.unit = extracted.unit


def merge_extraction(draft: PODraft, extraction: SlotExtraction,
                     resolver: EntityResolver) -> tuple[PODraft, list[Unresolved]]:
    d = draft.model_copy(deep=True)
    unresolved: list[Unresolved] = []

    if extraction.vendor:
        found = resolver.vendor(extraction.vendor)
        if found.match:
            d.vendor = found.match
        else:
            unresolved.append(Unresolved(kind="vendor", query=extraction.vendor, choices=[
                Option(v.id, v.name) for v in found.choices]))
    if extraction.currency:
        d.currency = extraction.currency
    if extraction.payment_terms:
        d.payment_terms = extraction.payment_terms
    if extraction.placed_on:
        d.placed_on = extraction.placed_on
    if extraction.expected_delivery_date:
        d.expected_delivery_date = extraction.expected_delivery_date
    if extraction.delivery_location:
        found_loc = resolver.location(extraction.delivery_location)
        if found_loc.match:
            d.delivery_location = found_loc.match
        else:
            unresolved.append(Unresolved(kind="location", query=extraction.delivery_location,
                                         choices=[Option(loc.id, loc.name)
                                                  for loc in found_loc.choices]))

    for extracted in extraction.lines:
        if extracted.action == "remove":
            target = _target(d, extracted.line)
            if target is not None:
                d.lines.remove(target)
                _renumber(d)
            continue
        if extracted.action == "update" and extracted.apply_to == "all":
            wanted = canonical_unit(extracted.for_unit) if extracted.for_unit else None
            for line in d.lines:
                unit = line.unit or (line.item.unit if line.item else None)
                if wanted is None or unit == wanted:
                    _set_fields(line, extracted.model_copy(update={"unit": None}), unresolved)
            continue
        if extracted.action == "update":
            target = _target(d, extracted.line)
            if target is None:
                continue
            if extracted.item:
                found_item = resolver.item(extracted.item)
                if found_item.match:
                    target.item = found_item.match
                    target.unit = None
            _set_fields(target, extracted, unresolved)
            continue
        found_item = resolver.item(extracted.item or "")
        if found_item.match is None:
            unresolved.append(Unresolved(
                kind="item", query=extracted.item or "", choices=[
                    Option(i.id, f"{i.name} ({i.code})") for i in found_item.choices],
                pending={k: str(v) for k, v in extracted.model_dump(
                    include={"quantity", "unit", "unit_price"}).items() if v is not None}))
            continue
        existing = next((ln for ln in d.lines if ln.item and ln.item.id == found_item.match.id),
                        None)
        if existing is not None:
            # The item is already on the draft: fill that line rather than adding it twice.
            _set_fields(existing, extracted, unresolved)
            continue
        line = POLine(position=len(d.lines) + 1, item=found_item.match)
        _set_fields(line, extracted, unresolved)
        d.lines.append(line)
    return d, unresolved


def _target(draft: PODraft, number: int | None) -> POLine | None:
    if number is not None:
        return next((line for line in draft.lines if line.position == number), None)
    return draft.lines[-1] if draft.lines else None


def apply_choice(draft: PODraft, kind: str, choice_id: str, catalog: Catalog,
                 **pending: Decimal | str | None) -> PODraft:
    d = draft.model_copy(deep=True)
    if kind == "vendor":
        d.vendor = next(v for v in catalog.vendors if v.id == choice_id)
    elif kind == "location":
        d.delivery_location = next(loc for loc in catalog.locations if loc.id == choice_id)
    elif kind == "item":
        item = next(i for i in catalog.items if i.id == choice_id)
        line = POLine(position=len(d.lines) + 1, item=item)
        for name in ("quantity", "unit_price"):
            if pending.get(name) is not None:
                setattr(line, name, Decimal(str(pending[name])))
        if pending.get("unit"):
            line.unit = str(pending["unit"])
        d.lines.append(line)
    elif kind == "payment_terms":
        d.payment_terms = choice_id
    return d
