"""Database access. Two engines on purpose:

* read engine:  every session is read-only with a statement timeout. Used by the SQL agent and
                the query buttons.
* write engine: used only by the PO, history and normalisation modules, with fixed SQL.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import Engine, create_engine


def sqlalchemy_url(url: str) -> str:
    """Accept plain postgres URLs and point SQLAlchemy at the psycopg 3 driver."""
    for prefix in ("postgresql+psycopg://", "postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    raise ValueError("Unsupported database URL scheme")


# Hosted Postgres sits behind TCP proxies that silently drop idle connections. Without these,
# a pooled connection can look alive and a query on it waits on a dead socket for minutes
# (the server-side statement_timeout can't help, the server never sees the query).
POOL_RECYCLE_SECONDS = 240
_LIVENESS: dict[str, int] = {
    "keepalives": 1,
    "keepalives_idle": 30,
    "keepalives_interval": 10,
    "keepalives_count": 3,
    "tcp_user_timeout": 15_000,  # ms; unacknowledged sends fail after this (Linux)
}


def read_options(statement_timeout_ms: int) -> str:
    return f"-c default_transaction_read_only=on -c statement_timeout={statement_timeout_ms}"


@dataclass(frozen=True)
class Database:
    read_engine: Engine
    write_engine: Engine
    read_connect_args: dict[str, Any] = field(default_factory=dict)
    write_connect_args: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def connect(cls, url: str, *, sslmode: str, statement_timeout_ms: int) -> Database:
        write_args: dict[str, Any] = {"sslmode": sslmode, "connect_timeout": 10, **_LIVENESS}
        read_args = {**write_args, "options": read_options(statement_timeout_ms)}
        pool = {"pool_pre_ping": True, "pool_recycle": POOL_RECYCLE_SECONDS}
        return cls(
            read_engine=create_engine(sqlalchemy_url(url), connect_args=read_args, **pool),
            write_engine=create_engine(sqlalchemy_url(url), connect_args=write_args, **pool),
            read_connect_args=read_args,
            write_connect_args=write_args,
        )

    def dispose(self) -> None:
        self.read_engine.dispose()
        self.write_engine.dispose()
