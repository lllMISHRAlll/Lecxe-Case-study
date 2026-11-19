import pytest

from tests.api.conftest import login


@pytest.mark.parametrize(("email", "count", "prefix"), [
    ("procurement@demo.local", 7, "pm_"), ("owner@demo.local", 6, "bo_"),
    ("warehouse@demo.local", 7, "wm_")])
def test_lists_the_roles_buttons(client, email, count, prefix):
    login(client, email)
    buttons = client.get("/api/canned").json()
    assert len(buttons) == count
    assert all(b["id"].startswith(prefix) for b in buttons)
    assert set(buttons[0]) == {"id", "label", "description"}


def test_needs_a_session(client):
    assert client.get("/api/canned").status_code == 401
