import uuid
from pathlib import Path

import pytest

from app.auth.passwords import verify_password
from app.auth.roles import Role
from app.auth.users import DEMO_USERS, UserDirectory


def test_auth_01_exactly_three_planned_users():
    users = {(u.email, u.name, u.role) for u in DEMO_USERS}
    assert users == {
        ("procurement@demo.local", "Arjun Rao", Role.PROCUREMENT_MANAGER),
        ("owner@demo.local", "Meera Iyer", Role.BUSINESS_OWNER),
        ("warehouse@demo.local", "Kabir Shah", Role.WAREHOUSE_MANAGER),
    }


def test_auth_02_fixed_unique_uuids():
    ids = [u.id for u in DEMO_USERS]
    assert len(set(ids)) == 3
    for value in ids:
        uuid.UUID(value)


def test_auth_03_only_a_hash_is_stored_and_it_verifies():
    source = Path("app/auth/users.py").read_text()
    assert "1234567890" not in source
    for user in DEMO_USERS:
        assert user.password_hash.startswith("$2b$")
        assert verify_password("1234567890", user.password_hash)
        assert not verify_password("wrong", user.password_hash)


@pytest.mark.parametrize("email", ["Owner@Demo.Local", "  owner@demo.local "])
def test_auth_08_lookup_is_case_insensitive_and_trimmed(email):
    assert UserDirectory().find_by_email(email).name == "Meera Iyer"


def test_unknown_email_returns_none():
    assert UserDirectory().find_by_email("nobody@demo.local") is None


def test_get_by_id():
    directory = UserDirectory()
    user = DEMO_USERS[0]
    assert directory.get(user.id) == user
    assert directory.get("missing") is None


def test_role_labels():
    assert Role.PROCUREMENT_MANAGER.label == "Procurement Manager"
    assert Role.BUSINESS_OWNER.label == "Business Owner"
    assert Role.WAREHOUSE_MANAGER.label == "Warehouse Manager"
