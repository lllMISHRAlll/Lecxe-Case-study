"""The data-cleaning changes applied in place to the company tables.

Each change says which rows it touches (`predicate`) and what their new values are.
The runner previews, backs up, applies, verifies and logs it.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from app.domain.vocabulary import UNIT_ALIASES, term_lookup


def lit(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


@dataclass(frozen=True)
class ColumnChange:
    column: str
    new_expr: str  # SQL expression over alias `t`
    cast: str  # SQL type used when restoring from the backup
    compare_as_text: bool = False


@dataclass(frozen=True)
class Change:
    id: str
    slug: str
    title: str
    reason: str
    table: str
    columns: tuple[ColumnChange, ...]
    extra_condition: str | None = None
    findings_sql: str | None = None
    verify_override: str | None = None

    @property
    def folder(self) -> str:
        return f"{self.id}_{self.slug}"

    @property
    def predicate(self) -> str:
        parts = []
        for c in self.columns:
            if c.compare_as_text:
                parts.append(f"t.{c.column}::text IS DISTINCT FROM ({c.new_expr})::text")
            else:
                parts.append(f"t.{c.column} IS DISTINCT FROM {c.new_expr}")
        condition = "(" + " OR ".join(parts) + ")"
        return f"{condition} AND {self.extra_condition}" if self.extra_condition else condition

    @property
    def preview_sql(self) -> str:
        selects = ", ".join(
            f"t.{c.column}::text AS old_{c.column}, ({c.new_expr})::text AS new_{c.column}"
            for c in self.columns
        )
        return f"SELECT t.id, {selects} FROM {self.table} AS t WHERE {self.predicate} ORDER BY t.id"

    @property
    def apply_sql(self) -> str:
        sets = ", ".join(f"{c.column} = {c.new_expr}" for c in self.columns)
        return f"UPDATE {self.table} AS t SET {sets} WHERE {self.predicate}"

    @property
    def verify_sql(self) -> str:
        return self.verify_override or (
            f"SELECT count(*) FROM {self.table} AS t WHERE {self.predicate}"
        )

    def with_verify_sql(self, sql: str) -> Change:
        return replace(self, verify_override=sql)


def _mapping_case(column: str, mapping: dict[str, str], key_expr: str,
                  blank_to_null: bool = False) -> str:
    whens = [f"WHEN {lit(raw)} THEN {lit(canonical)}" for raw, canonical in mapping.items()]
    if blank_to_null:
        whens.insert(0, "WHEN '' THEN NULL")
    return f"CASE {key_expr} {' '.join(whens)} ELSE t.{column} END"


def _unknown_values_sql(table: str, column: str, key_expr: str, known: dict[str, str],
                        label: str) -> str:
    keys = ", ".join(lit(k) for k in [*known, ""])
    return (
        f"SELECT 'Unknown {label} ' || quote_literal(t.{column}) || ' on ' || count(*) "
        f"|| ' row(s) left unchanged' FROM {table} AS t "
        f"WHERE t.{column} IS NOT NULL AND {key_expr} NOT IN ({keys}) GROUP BY t.{column}"
    )


def _unit_change() -> Change:
    key = "lower(btrim(t.unit))"
    return Change(
        id="001", slug="po_line_units", title="PO line units",
        reason="Unit spellings on PO lines (KG, Nos., Unit, Set, Ltr, Mtr) aligned to the item "
               "unit vocabulary so quantities can be compared.",
        table="proc_po_lines",
        columns=(ColumnChange("unit", _mapping_case("unit", UNIT_ALIASES, key), "varchar"),),
        findings_sql=_unknown_values_sql("proc_po_lines", "unit", key, UNIT_ALIASES, "unit"),
    )


def _term_change(change_id: str, slug: str, title: str, table: str, column: str,
                 *, stages: bool = False, blank_to_null: bool = True) -> Change:
    key = f"lower(regexp_replace(btrim(t.{column}), '\\s+', ' ', 'g'))"
    mapping = term_lookup(include_stages=stages)
    return Change(
        id=change_id, slug=slug, title=title,
        reason="Payment-term spellings collapsed to canonical terms"
               + (", empty strings set to NULL." if blank_to_null else "."),
        table=table,
        columns=(ColumnChange(column, _mapping_case(column, mapping, key, blank_to_null),
                              "varchar"),),
        findings_sql=_unknown_values_sql(table, column, key, mapping, "payment term"),
    )


def _name_change() -> Change:
    expr = "regexp_replace(btrim(t.name), '\\s+', ' ', 'g')"
    collision = f"EXISTS (SELECT 1 FROM inv_items AS o WHERE o.id <> t.id AND o.name = {expr})"
    return Change(
        id="005", slug="item_name_spaces", title="Item name spaces",
        reason="Leading, trailing and repeated spaces removed from item names. Names that would "
               "then equal another item's name are skipped and reported.",
        table="inv_items",
        columns=(ColumnChange("name", expr, "varchar"),),
        extra_condition=f"NOT {collision}",
        findings_sql=(
            "SELECT 'Item ' || t.item_code || ' (' || quote_literal(t.name) || ') not trimmed: "
            f"the trimmed name already belongs to another item' FROM inv_items AS t "
            f"WHERE t.name <> {expr} AND {collision}"
        ),
    )


def _date_list_change(change_id: str, slug: str, title: str, table: str) -> Change:
    return Change(
        id=change_id, slug=slug, title=title,
        reason="NULL expected-date lists replaced with [] so every row uses one empty form.",
        table=table,
        columns=tuple(
            ColumnChange(col, f"COALESCE(t.{col}, '[]'::json)", "json", compare_as_text=True)
            for col in ("expected_delivery_date", "expected_dispatch_date")
        ),
    )


CHANGES: tuple[Change, ...] = (
    _unit_change(),
    _term_change("002", "po_payment_terms", "PO payment terms", "proc_purchase_orders",
                 "payment_terms"),
    _term_change("003", "vendor_payment_terms", "Vendor payment terms", "proc_vendors",
                 "payment_terms"),
    _term_change("004", "tranche_stages", "Payment tranche stages", "proc_po_payment_tranches",
                 "stage", stages=True, blank_to_null=False),
    _name_change(),
    _date_list_change("006", "po_date_lists", "PO header date lists", "proc_purchase_orders"),
    _date_list_change("007", "po_line_date_lists", "PO line date lists", "proc_po_lines"),
)


def change_by_id(change_id: str) -> Change:
    for change in CHANGES:
        if change.id == change_id:
            return change
    raise KeyError(change_id)
