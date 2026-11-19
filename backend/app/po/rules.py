"""Business rules for a PO draft: defaults, review, and which question to ask next."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from app.domain.vocabulary import CANONICAL_TERMS, CANONICAL_UNITS, canonical_term, canonical_unit
from app.po.catalog import Catalog
from app.po.models import PODraft
from app.po.totals import Totals, draft_totals

SLOT_ORDER = ("vendor", "item", "quantity", "unit_price", "payment_terms")


@dataclass(frozen=True)
class Option:
    id: str
    label: str


@dataclass(frozen=True)
class Question:
    slot: str
    text: str
    line: int | None = None
    options: list[Option] = field(default_factory=list)


@dataclass
class Review:
    draft: PODraft
    missing_slots: list[tuple[str, int | None]]
    errors: list[str]
    line_warnings: dict[int, list[str]]
    defaults_used: list[str]
    totals: Totals

    @property
    def missing(self) -> list[str]:
        return list(dict.fromkeys(slot for slot, _ in self.missing_slots))

    @property
    def complete(self) -> bool:
        return not self.missing_slots and not self.errors


def apply_defaults(draft: PODraft, today: date) -> PODraft:
    d = draft.model_copy(deep=True)
    if d.placed_on is None:
        d.placed_on = today
    if d.payment_terms:
        d.payment_terms = canonical_term(d.payment_terms)
    elif d.vendor and d.vendor.payment_terms:
        d.payment_terms = canonical_term(d.vendor.payment_terms)
        note = f"Payment terms set to the vendor's usual: {d.payment_terms}"
        if note not in d.defaults_used:
            d.defaults_used = [*d.defaults_used, note]
    for line in d.lines:
        if line.item and not line.unit:
            line.unit = line.item.unit
        elif line.unit:
            line.unit = canonical_unit(line.unit) or line.unit
    return d


def suggest_prices(draft: PODraft, catalog: Catalog) -> PODraft:
    d = draft.model_copy(deep=True)
    for line in d.lines:
        if line.item and line.unit_price is None:
            line.suggested_price = catalog.last_price(
                line.item.id, d.vendor.id if d.vendor else None, d.currency)
    return d


def review(draft: PODraft) -> Review:
    missing: list[tuple[str, int | None]] = []
    errors: list[str] = []
    warnings: dict[int, list[str]] = {}

    if draft.vendor is None:
        missing.append(("vendor", None))
    elif not draft.vendor.is_active:
        errors.append(f"{draft.vendor.name} is not an active vendor.")
    if not draft.lines:
        missing.append(("item", None))
    for line in draft.lines:
        if line.item is None:
            missing.append(("item", line.position))
            continue
        if not line.item.is_active:
            errors.append(f"{line.item.name} is not an active item.")
        if line.quantity is None:
            missing.append(("quantity", line.position))
        if line.unit_price is None:
            missing.append(("unit_price", line.position))
        if line.unit and line.unit not in CANONICAL_UNITS:
            errors.append(f"Unit {line.unit} is not recognised. Use one of: "
                          f"{', '.join(sorted(CANONICAL_UNITS))}.")
        elif line.unit and line.unit != line.item.unit:
            warnings.setdefault(line.position, []).append(
                f"Unit {line.unit} differs from the stock unit {line.item.unit}.")
    if draft.payment_terms is None:
        missing.append(("payment_terms", None))
    elif draft.payment_terms not in CANONICAL_TERMS:
        errors.append(f"Payment terms '{draft.payment_terms}' are not recognised. Choose one of "
                      "the standard terms.")

    order = {slot: i for i, slot in enumerate(SLOT_ORDER)}
    missing.sort(key=lambda m: (order[m[0]] if m[0] != "item" or m[1] is None else 1,
                                m[1] or 0))
    return Review(draft, missing, errors, warnings, list(draft.defaults_used),
                  draft_totals(draft.lines))


def next_question(rev: Review) -> Question | None:
    if rev.errors:
        return Question("fix", rev.errors[0])
    if not rev.missing_slots:
        return None
    slot, position = rev.missing_slots[0]
    draft = rev.draft
    line = next((ln for ln in draft.lines if ln.position == position), None)
    if slot == "vendor":
        return Question(slot, "Which vendor is this PO for?")
    if slot == "item":
        return Question(slot, "Which item should I add? You can give the item code or name.")
    if slot == "payment_terms" or line is None or line.item is None:
        vendor = draft.vendor.name if draft.vendor else "This vendor"
        return Question("payment_terms",
                        f"Which payment terms apply? {vendor} has no usual terms on record.",
                        options=[Option(term, term) for term in CANONICAL_TERMS])
    same = [ln for ln in draft.lines
            if ln.item and (slot, ln.position) in rev.missing_slots]
    if len(same) > 1:
        return _grouped_question(slot, same, draft.currency)
    unit = line.unit or line.item.unit
    if slot == "quantity":
        return Question(slot, f"How many {unit} of {line.item.name}?", line=position)
    hint = ""
    if line.suggested_price is not None:
        symbol = "₹" if draft.currency == "INR" else "$"
        hint = f" The last price paid was {symbol}{line.suggested_price:f}."
    return Question("unit_price", f"What's the price per {unit} for {line.item.name}?{hint}",
                    line=position)


def _grouped_question(slot: str, lines: list, currency: str) -> Question:
    symbol = "₹" if currency == "INR" else "$"
    listed = []
    for ln in lines:
        unit = ln.unit or ln.item.unit
        hint = (f", last paid {symbol}{ln.suggested_price:f}"
                if slot == "unit_price" and ln.suggested_price is not None else "")
        listed.append(f"{ln.position}. {ln.item.name} ({unit}{hint})")
    if slot == "quantity":
        lead = f"How many of each? {len(lines)} items still need a quantity:"
        how = "Reply for all at once, e.g. 'all 10 pcs and 2 kg', or per line, e.g. 'line 1: 5'."
    else:
        lead = f"What's the price per unit for each? {len(lines)} items still need a price:"
        how = "Reply per line, e.g. 'line 1: 450, line 2: 85', or 'all at 120'."
    return Question(slot, "\n".join([lead, *listed, how]))
