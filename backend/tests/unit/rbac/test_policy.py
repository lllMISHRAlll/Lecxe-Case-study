import pytest

from app.auth.roles import Role
from app.rbac.capabilities import Capability, has_capability
from app.rbac.scope import can_access_table, tables_for

PM, BO, WM = Role.PROCUREMENT_MANAGER, Role.BUSINESS_OWNER, Role.WAREHOUSE_MANAGER

MATRIX = {
    Capability.CHAT_ASK: {PM: True, BO: True, WM: True},
    Capability.CANNED_RUN: {PM: True, BO: True, WM: True},
    Capability.PO_CREATE: {PM: True, BO: False, WM: False},
    Capability.HISTORY_OWN: {PM: True, BO: True, WM: True},
    Capability.FEEDBACK_SEND: {PM: True, BO: True, WM: True},
}


@pytest.mark.parametrize(("capability", "role"),
                         [(c, r) for c in MATRIX for r in (PM, BO, WM)])
def test_rbac_01_capability_matrix(capability, role):
    assert has_capability(role, capability) is MATRIX[capability][role]


def test_rbac_02_only_procurement_manager_can_create_pos():
    assert [r for r in Role if has_capability(r, Capability.PO_CREATE)] == [PM]


def test_rbac_03_warehouse_manager_cannot_see_payment_tranches():
    assert not can_access_table(WM, "proc_po_payment_tranches")
    assert can_access_table(PM, "proc_po_payment_tranches")
    assert can_access_table(BO, "proc_po_payment_tranches")


@pytest.mark.parametrize("role", list(Role))
@pytest.mark.parametrize("table", ["inv_field_definitions", "assistant.conversations",
                                   "assistant.messages", "pg_catalog.pg_user", "unknown_table"])
def test_rbac_04_nobody_reaches_config_app_or_unknown_tables(role, table):
    assert not can_access_table(role, table)


def test_table_names_are_case_insensitive_and_schema_public_is_allowed():
    assert can_access_table(PM, "PUBLIC.Proc_Vendors")
    assert can_access_table(PM, "proc_vendors")


def test_business_owner_and_pm_see_all_business_tables():
    assert len(tables_for(BO)) == 16
    assert tables_for(PM) == tables_for(BO)
    assert tables_for(WM) == tables_for(BO) - {"proc_po_payment_tranches"}
