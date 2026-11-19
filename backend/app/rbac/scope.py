"""Which tables each role may query through the assistant.

Written as table -> columns so column-level rules can be added later; today every allowed
table is allowed in full (ALL).
"""

from __future__ import annotations

from app.auth.roles import Role

ALL = "*"

_BUSINESS_TABLES = frozenset({
    "inv_categories", "inv_sub_categories", "inv_sub_categories_2", "inv_items",
    "inv_locations", "inv_current_stock", "inv_issued_to_targets", "inv_transactions",
    "proc_vendors", "proc_purchase_orders", "proc_po_lines", "proc_po_payment_tranches",
    "proc_po_receipts", "proc_po_line_regularisations", "proc_unexpected_receipt_headers",
    "proc_unexpected_receipts",
})

ROLE_SCOPES: dict[Role, dict[str, str]] = {
    Role.PROCUREMENT_MANAGER: dict.fromkeys(_BUSINESS_TABLES, ALL),
    Role.BUSINESS_OWNER: dict.fromkeys(_BUSINESS_TABLES, ALL),
    Role.WAREHOUSE_MANAGER: dict.fromkeys(_BUSINESS_TABLES - {"proc_po_payment_tranches"}, ALL),
}


def normalise_table_name(name: str) -> str | None:
    """'PUBLIC.Proc_Vendors' -> 'proc_vendors'. Other schemas -> None (never allowed)."""
    parts = name.strip().lower().split(".")
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2 and parts[0] == "public":
        return parts[1]
    return None


def tables_for(role: Role) -> frozenset[str]:
    return frozenset(ROLE_SCOPES[role])


def can_access_table(role: Role, name: str) -> bool:
    table = normalise_table_name(name)
    return table is not None and table in ROLE_SCOPES[role]
