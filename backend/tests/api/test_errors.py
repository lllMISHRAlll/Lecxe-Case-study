from fastapi.testclient import TestClient

from app.main import create_app


def test_out_04_unexpected_errors_hide_internals_and_carry_a_reference(settings, api_clock):
    app = create_app(settings=settings, clock=api_clock)

    @app.get("/api/boom")
    def boom():
        raise RuntimeError('relation "secret_table" does not exist at host db.internal')

    response = TestClient(app, raise_server_exceptions=False).get("/api/boom")

    assert response.status_code == 500
    error = response.json()["error"]
    assert error["code"] == "internal_error"
    assert len(error["reference"]) == 8
    assert "secret_table" not in response.text
    assert "db.internal" not in response.text
