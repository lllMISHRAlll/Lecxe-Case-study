"""Alembic environment. Only ever touches the `assistant` schema."""

from alembic import context
from sqlalchemy import create_engine, text

from app.db.sessions import sqlalchemy_url

SCHEMA = "assistant"
config = context.config
url = config.attributes["url"]
sslmode = config.attributes.get("sslmode", "require")

engine = create_engine(sqlalchemy_url(url), connect_args={"sslmode": sslmode})
with engine.begin() as conn:
    conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}"))

with engine.connect() as connection:
    context.configure(
        connection=connection,
        version_table_schema=SCHEMA,
        include_schemas=False,
    )
    with context.begin_transaction():
        context.run_migrations()
engine.dispose()
