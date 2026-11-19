"""Builds the role-filtered schema text the LLM sees."""

from __future__ import annotations

from collections.abc import Iterable

from app.auth.roles import Role
from app.rbac.scope import tables_for
from app.sql.dictionary import DICTIONARY, TableDoc


def schema_for(role: Role, only: Iterable[str] | None = None) -> list[TableDoc]:
    allowed = tables_for(role)
    wanted = allowed if only is None else allowed & {t.lower() for t in only}
    return [DICTIONARY[name] for name in sorted(wanted)]


def render_schema(role: Role, only: Iterable[str] | None = None) -> str:
    blocks = []
    for table in schema_for(role, only):
        lines = [f"TABLE {table.name}: {table.description}"]
        for column, doc in table.columns.items():
            values = f" Values: {', '.join(doc.values)}." if doc.values else ""
            lines.append(f"  - {column} ({doc.type}): {doc.description}{values}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)
