import pytest

from app.db.sessions import Database, read_options, sqlalchemy_url


def test_db_04_connections_require_ssl_and_read_sessions_are_read_only():
    db = Database.connect("postgresql://u:p@example.invalid:5432/x", sslmode="require",
                          statement_timeout_ms=5000)
    try:
        assert db.read_engine.dialect.create_connect_args(db.read_engine.url)[1].get(
            "sslmode") in (None, "require")
        read_args = db.read_connect_args
        assert read_args["sslmode"] == "require"
        assert "default_transaction_read_only=on" in read_args["options"]
        assert "statement_timeout=5000" in read_args["options"]
        assert db.write_connect_args["sslmode"] == "require"
        assert "options" not in db.write_connect_args
    finally:
        db.dispose()


def test_read_options():
    assert read_options(250) == "-c default_transaction_read_only=on -c statement_timeout=250"


@pytest.mark.parametrize("url", ["postgresql://a@h/d", "postgres://a@h/d",
                                 "postgresql+psycopg://a@h/d"])
def test_urls_use_psycopg(url):
    assert sqlalchemy_url(url) == "postgresql+psycopg://a@h/d"


def test_unknown_scheme_rejected():
    with pytest.raises(ValueError):
        sqlalchemy_url("mysql://a@h/d")


def test_connections_survive_proxies_that_drop_idle_sockets():
    db = Database.connect("postgresql://u:p@example.invalid:5432/x", sslmode="require",
                          statement_timeout_ms=5000)
    try:
        for args in (db.read_connect_args, db.write_connect_args):
            assert args["keepalives"] == 1
            assert args["keepalives_idle"] <= 30
            assert args["tcp_user_timeout"] <= 15_000  # a dead socket fails fast, not after minutes
        for engine in (db.read_engine, db.write_engine):
            assert engine.pool._pre_ping is True
            assert 0 < engine.pool._recycle <= 300
    finally:
        db.dispose()
