from decimal import Decimal

from app.po.models import PODraft, POLine
from app.po.resolver import EntityResolver
from app.po.slots import ExtractedLine, SlotExtraction, merge_extraction
from tests.fixtures.po_catalog import catalog

CAT = catalog()
resolver = EntityResolver(CAT)


def test_po_11_exact_item_code_wins():
    result = resolver.item("bo-mc-0001")
    assert result.match.name == "Hex Nut M8"


def test_po_11_fuzzy_item_name():
    assert resolver.item("ms tube 25x40").match.code == "RM-MT-0001"
    assert resolver.item("relay 240v").match.code == "BO-EL-0001"


def test_po_11_several_close_matches_become_choices():
    result = resolver.item("hex nut")
    assert result.match is None
    assert {c.code for c in result.choices} == {"BO-MC-0001", "BO-MC-0004"}


def test_po_11_no_match():
    result = resolver.item("unobtainium widget")
    assert result.match is None and result.choices == []


def test_vendor_fuzzy_and_ambiguous():
    assert resolver.vendor("anand").match.id == "v-anand"
    zenith = resolver.vendor("zenith")
    assert zenith.match is None
    assert {v.id for v in zenith.choices} == {"v-zenith", "v-zen2"}
    assert resolver.vendor("zenith steels").match.id == "v-zenith"


def test_po_06_inactive_entities_are_never_resolved():
    assert resolver.vendor("Old Traders").match is None
    assert resolver.item("Old Bracket").match is None


def test_po_12_last_price_prefers_same_vendor_and_currency():
    assert CAT.last_price("i-tube", "v-zenith", "INR") == Decimal("88")
    assert CAT.last_price("i-tube", "v-summit", "INR") == Decimal("80")  # latest any vendor
    assert CAT.last_price("i-relay", "v-zenith", "INR") == Decimal("450")  # same currency only
    assert CAT.last_price("i-hinge", "v-zenith", "INR") is None


def draft_with(*lines):
    return PODraft(idempotency_key="k", lines=list(lines))


def test_po_09_extraction_fills_the_draft():
    extraction = SlotExtraction(
        vendor="Zenith Steels",
        payment_terms=None,
        lines=[ExtractedLine(item="MS tube 25x40", quantity=50, unit="kg", unit_price=120)],
    )
    d, unresolved = merge_extraction(draft_with(), extraction, resolver)
    assert d.vendor.id == "v-zenith"
    assert d.lines[0].item.code == "RM-MT-0001"
    assert (d.lines[0].quantity, d.lines[0].unit_price) == (Decimal(50), Decimal(120))
    assert unresolved == []


def test_po_10_change_price_on_the_only_line():
    tube = resolver.item("RM-MT-0001").match
    d = draft_with(POLine(position=1, item=tube, quantity=Decimal(50), unit_price=Decimal(120)))
    d, _ = merge_extraction(
        d, SlotExtraction(lines=[ExtractedLine(action="update", unit_price=115)]), resolver
    )
    assert d.lines[0].unit_price == Decimal(115)


def test_po_10_add_a_line():
    tube = resolver.item("RM-MT-0001").match
    d = draft_with(POLine(position=1, item=tube, quantity=Decimal(50), unit_price=Decimal(120)))
    d, _ = merge_extraction(
        d, SlotExtraction(lines=[ExtractedLine(item="BO-EL-0001", quantity=10)]), resolver
    )
    assert [line.position for line in d.lines] == [1, 2]
    assert d.lines[1].item.code == "BO-EL-0001"


def test_po_10_remove_a_line_and_renumber():
    tube, relay = resolver.item("RM-MT-0001").match, resolver.item("BO-EL-0001").match
    d = draft_with(POLine(position=1, item=tube), POLine(position=2, item=relay))
    d, _ = merge_extraction(
        d, SlotExtraction(lines=[ExtractedLine(action="remove", line=1)]), resolver
    )
    assert [(line.position, line.item.code) for line in d.lines] == [(1, "BO-EL-0001")]


def test_po_10_change_quantity_on_a_named_line():
    tube, relay = resolver.item("RM-MT-0001").match, resolver.item("BO-EL-0001").match
    d = draft_with(POLine(position=1, item=tube), POLine(position=2, item=relay))
    d, _ = merge_extraction(
        d, SlotExtraction(lines=[ExtractedLine(action="update", line=2, quantity=7)]), resolver
    )
    assert d.lines[1].quantity == Decimal(7)


def test_ambiguous_vendor_is_returned_as_unresolved_choices():
    d, unresolved = merge_extraction(draft_with(), SlotExtraction(vendor="zenith"), resolver)
    assert d.vendor is None
    assert unresolved[0].kind == "vendor"
    assert len(unresolved[0].choices) == 2


def test_unknown_item_is_reported():
    d, unresolved = merge_extraction(
        draft_with(),
        SlotExtraction(lines=[ExtractedLine(item="unobtainium widget", quantity=1)]),
        resolver,
    )
    assert d.lines == []
    assert unresolved[0].kind == "item"
    assert unresolved[0].choices == []


def test_choosing_an_option_resolves_it():
    from app.po.slots import apply_choice

    d = apply_choice(draft_with(), "vendor", "v-zen2", CAT)
    assert d.vendor.name == "Zenith Automation"
    d = apply_choice(d, "item", "i-nut10", CAT, quantity=Decimal(5))
    assert d.lines[0].item.code == "BO-MC-0004"


def test_adding_an_item_already_on_the_draft_fills_that_line_instead_of_duplicating():
    tube, relay = resolver.item("RM-MT-0001").match, resolver.item("BO-EL-0001").match
    d = draft_with(POLine(position=1, item=tube), POLine(position=2, item=relay))
    d, _ = merge_extraction(
        d,
        SlotExtraction(
            lines=[
                ExtractedLine(item="RM-MT-0001", quantity=2),
                ExtractedLine(item="BO-EL-0001", quantity=10),
            ]
        ),
        resolver,
    )
    assert [(ln.position, ln.item.code, ln.quantity) for ln in d.lines] == [
        (1, "RM-MT-0001", Decimal(2)),
        (2, "BO-EL-0001", Decimal(10)),
    ]


def test_update_all_lines_by_unit():
    tube, relay = resolver.item("RM-MT-0001").match, resolver.item("BO-EL-0001").match
    nut = resolver.item("BO-MC-0001").match
    d = draft_with(
        POLine(position=1, item=tube, unit="kg"),
        POLine(position=2, item=relay, unit="pcs"),
        POLine(position=3, item=nut, unit="pcs"),
    )
    d, _ = merge_extraction(
        d,
        SlotExtraction(
            lines=[
                ExtractedLine(action="update", apply_to="all", for_unit="pcs", quantity=10),
                ExtractedLine(action="update", apply_to="all", for_unit="KG", quantity=2),
            ]
        ),
        resolver,
    )
    assert [ln.quantity for ln in d.lines] == [Decimal(2), Decimal(10), Decimal(10)]


def test_update_all_lines_without_a_unit_filter():
    tube, relay = resolver.item("RM-MT-0001").match, resolver.item("BO-EL-0001").match
    d = draft_with(POLine(position=1, item=tube), POLine(position=2, item=relay))
    d, _ = merge_extraction(
        d,
        SlotExtraction(lines=[ExtractedLine(action="update", apply_to="all", unit_price=99)]),
        resolver,
    )
    assert [ln.unit_price for ln in d.lines] == [Decimal(99), Decimal(99)]
