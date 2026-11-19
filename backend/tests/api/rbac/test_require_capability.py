from typing import Annotated

from fastapi import Depends
from fastapi.testclient import TestClient

from app.api.deps import require
from app.auth.users import User
from app.main import create_app
from app.rbac.capabilities import Capability
from tests.api.conftest import login


def client_with_po_route(settings, api_clock):
    app = create_app(settings=settings, clock=api_clock)

    @app.post("/api/test-po")
    def create_po(user: Annotated[User, Depends(require(Capability.PO_CREATE))]):
        return {"ok": user.name}

    return TestClient(app)


def test_require_rejects_anonymous_with_401(settings, api_clock):
    assert client_with_po_route(settings, api_clock).post("/api/test-po").status_code == 401


def test_require_rejects_roles_without_the_capability(settings, api_clock):
    for email in ("owner@demo.local", "warehouse@demo.local"):
        client = client_with_po_route(settings, api_clock)
        login(client, email)
        response = client.post("/api/test-po")
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "forbidden"


def test_require_allows_the_procurement_manager(settings, api_clock):
    client = client_with_po_route(settings, api_clock)
    login(client)
    assert client.post("/api/test-po").json() == {"ok": "Arjun Rao"}


def test_rbac_07_every_real_route_except_public_ones_needs_a_session(client):
    public = {"/api/health", "/api/auth/login", "/api/auth/demo-users", "/api/auth/logout",
              "/api/docs", "/api/openapi.json", "/api/docs/oauth2-redirect"}
    for route in client.app.routes:
        path = getattr(route, "path", "")
        if not path.startswith("/api") or path in public or "{" in path:
            continue
        for method in getattr(route, "methods", set()) - {"HEAD", "OPTIONS"}:
            response = client.request(method, path)
            assert response.status_code == 401, (method, path)
