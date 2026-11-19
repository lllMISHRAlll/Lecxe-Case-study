import pytest

from tests.api.conftest import login

USERS = [
    ("procurement@demo.local", "Arjun Rao", "procurement_manager", "Procurement Manager"),
    ("owner@demo.local", "Meera Iyer", "business_owner", "Business Owner"),
    ("warehouse@demo.local", "Kabir Shah", "warehouse_manager", "Warehouse Manager"),
]


@pytest.mark.parametrize(("email", "name", "role", "label"), USERS)
def test_auth_04_login_succeeds_for_each_user(client, email, name, role, label):
    response = login(client, email)

    assert response.status_code == 200
    user = response.json()["user"]
    assert (user["name"], user["role"], user["role_label"]) == (name, role, label)


def test_auth_05_cookie_flags_in_dev(client):
    cookie = login(client).headers["set-cookie"].lower()

    assert "pa_session=" in cookie
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    assert "path=/" in cookie
    assert "secure" not in cookie


def test_auth_05_cookie_is_secure_in_prod(make_client):
    cookie = login(make_client(app_env="prod")).headers["set-cookie"].lower()

    assert "secure" in cookie


def test_auth_06_wrong_password_is_401_with_generic_message(client):
    response = login(client, password="nope")

    assert response.status_code == 401
    error = response.json()["error"]
    assert error["code"] == "invalid_credentials"
    assert error["reference"]


def test_auth_07_unknown_email_gives_identical_message(client):
    wrong_password = login(client, password="nope").json()["error"]["message"]
    unknown_email = login(client, email="ghost@demo.local").json()["error"]["message"]

    assert wrong_password == unknown_email


def test_auth_08_email_case_and_spaces_ignored(client):
    assert login(client, email="  PROCUREMENT@demo.local ").status_code == 200


@pytest.mark.parametrize("body", [{}, {"email": "x"}, {"email": "a@b.c", "password": 5},
                                  {"email": "not-an-email", "password": "x"}])
def test_auth_09_malformed_body_is_422(client, body):
    response = client.post("/api/auth/login", json=body)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


def test_auth_14_me_returns_user_and_needs_a_session(client):
    assert client.get("/api/auth/me").status_code == 401
    login(client, "owner@demo.local")

    me = client.get("/api/auth/me")

    assert me.status_code == 200
    assert me.json()["user"]["name"] == "Meera Iyer"


def test_auth_11_expired_session_is_401(client, api_clock):
    login(client)
    api_clock.advance(hours=8, seconds=1)

    assert client.get("/api/auth/me").status_code == 401


def test_auth_15_logout_clears_the_cookie(client):
    login(client)

    response = client.post("/api/auth/logout")

    assert response.status_code == 204
    assert 'pa_session=""' in response.headers["set-cookie"] or "max-age=0" in (
        response.headers["set-cookie"].lower())
    assert client.get("/api/auth/me").status_code == 401


def test_auth_16_eleventh_login_attempt_in_a_minute_is_429(client, api_clock):
    for _ in range(10):
        assert login(client, password="nope").status_code == 401

    assert login(client, password="nope").status_code == 429

    api_clock.advance(seconds=61)
    assert login(client, password="nope").status_code == 401


def test_demo_users_endpoint_lists_quick_logins_with_password_outside_prod(client, make_client):
    users = client.get("/api/auth/demo-users").json()
    assert {u["email"] for u in users} == {u[0] for u in USERS}
    assert all(u["password"] == "1234567890" for u in users)

    prod_users = make_client(app_env="prod").get("/api/auth/demo-users").json()
    assert all(u["password"] is None for u in prod_users)


def test_health_needs_no_auth(client):
    assert client.get("/api/health").json() == {"status": "ok"}
