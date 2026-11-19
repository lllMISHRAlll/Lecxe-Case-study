from app.auth.roles import Role
from app.rbac.schema_filter import render_schema, schema_for


def test_rbac_05_schema_contains_only_the_roles_tables():
    names = {t.name for t in schema_for(Role.WAREHOUSE_MANAGER)}
    assert "proc_po_payment_tranches" not in names
    assert "inv_current_stock" in names

    text = render_schema(Role.WAREHOUSE_MANAGER)
    assert "proc_po_payment_tranches" not in text
    assert "inv_field_definitions" not in text
    assert "inv_current_stock" in text


def test_render_schema_can_be_narrowed_to_selected_tables():
    text = render_schema(Role.BUSINESS_OWNER, only=["proc_vendors"])
    assert "proc_vendors" in text
    assert "proc_purchase_orders" not in text


def test_rendered_schema_includes_descriptions_and_allowed_values():
    text = render_schema(Role.BUSINESS_OWNER, only=["proc_purchase_orders"])
    assert "placed" in text and "partial" in text and "received" in text
    assert "JSON list" in text


def test_narrowing_never_widens_access():
    text = render_schema(Role.WAREHOUSE_MANAGER, only=["proc_po_payment_tranches"])
    assert "proc_po_payment_tranches" not in text
