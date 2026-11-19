"""SQL agent nodes: link schema, generate, validate (parse + policy + EXPLAIN), fix."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.agents.deps import GraphDeps
from app.agents.events import emit, step
from app.agents.prompts.sql import (
    FIX_SYSTEM,
    FIX_USER,
    GENERATE_SYSTEM,
    GENERATE_USER,
    SCHEMA_LINK_SYSTEM,
)
from app.agents.sql_agent.hints import examples, strip_fences, value_hints
from app.agents.state import AgentState
from app.llm.tasks import Task
from app.rbac.schema_filter import render_schema, schema_for
from app.rbac.scope import tables_for
from app.sql.validator import SqlRejectedError

MAX_ATTEMPTS = 3

NOT_ANSWERABLE = ("I can't answer that from the procurement and inventory data available to "
                  "your role. Try asking about vendors, purchase orders, payments, receipts or "
                  "stock.")
GAVE_UP = ("Sorry, I couldn't build a query that answers that. Try rephrasing it, or use one "
           "of the suggested questions.")


class LinkedSchema(BaseModel):
    answerable: bool
    tables: list[str] = Field(default_factory=list)
    reason: str = ""


class SqlAgentNodes:
    def __init__(self, deps: GraphDeps) -> None:
        self.d = deps

    def _schema(self, state: AgentState) -> str:
        role = state["user"].role
        return render_schema(role, only=state.get("linked_tables") or None)

    def schema_link(self, state: AgentState) -> dict[str, Any]:
        role = state["user"].role
        catalogue = "\n".join(f"- {t.name}: {t.description}" for t in schema_for(role))
        linked = self.d.llm.structured(
            Task.SCHEMA_LINK, system=SCHEMA_LINK_SYSTEM, schema=LinkedSchema,
            user=f"Tables:\n{catalogue}\n\nQuestion: {state['question']}")
        tables = [t for t in linked.tables if t.lower() in tables_for(role)]
        step("schema_link", "Found the relevant tables")
        if not linked.answerable or not tables:
            return {"gave_up": True, "reply": NOT_ANSWERABLE, "reply_mode": "text"}
        return {"linked_tables": tables, "gave_up": False}

    def generate_sql(self, state: AgentState) -> dict[str, Any]:
        settings, today = self.d.settings, self.d.clock.today()
        user_prompt = GENERATE_USER.format(
            schema=self._schema(state),
            hints=value_hints(state["question"], self.d.load_catalog()),
            examples=examples(state["question"], state["user"].role, self.d.registry, today,
                              settings.fx_usd_inr),
            question=state["question"])
        sql = strip_fences(self.d.llm.text(
            Task.GENERATE_SQL, user=user_prompt,
            system=GENERATE_SYSTEM.format(today=today.isoformat(), fx=f"{settings.fx_usd_inr:g}")))
        step("generate_sql", "Wrote a query")
        return {"sql": sql, "sql_source": "generated", "attempts": 1, "sql_errors": [],
                "sql_params": {}}

    def validate_sql(self, state: AgentState) -> dict[str, Any]:
        def show(sql: str) -> None:
            emit("sql", {"sql": sql, "source": state.get("sql_source", "generated"),
                         "attempt": state.get("attempts", 1)})

        try:
            validated = self.d.validator.validate(state["sql"] or "", state["user"].role)
            self.d.explainer.check(validated.sql)
        except SqlRejectedError as exc:
            show(state["sql"] or "")
            step("validate_sql", "Query needs a fix")
            update: dict[str, Any] = {"sql_errors": [*state.get("sql_errors", []), str(exc)],
                                      "sql_valid": False}
            if state.get("attempts", 1) >= MAX_ATTEMPTS:
                update |= {"gave_up": True, "reply": GAVE_UP, "reply_mode": "text"}
            return update
        show(validated.sql)
        step("validate_sql", "Checked the query")
        return {"sql": validated.sql, "sql_valid": True}

    def fix_sql(self, state: AgentState) -> dict[str, Any]:
        settings, today = self.d.settings, self.d.clock.today()
        attempt = state.get("attempts", 1) + 1
        sql = strip_fences(self.d.llm.text(
            Task.FIX_SQL,
            system=FIX_SYSTEM.format(today=today.isoformat(), fx=f"{settings.fx_usd_inr:g}"),
            user=FIX_USER.format(schema=self._schema(state), question=state["question"],
                                 sql=state.get("sql") or "", error=state["sql_errors"][-1])))
        step("fix_sql", f"Fixed the query (attempt {attempt})")
        return {"sql": sql, "sql_source": "fixed", "attempts": attempt}

    # ------------------------------------------------------------------ routing

    @staticmethod
    def entry(state: AgentState) -> str:
        return "fix_sql" if state.get("sql_errors") and state.get("sql") else "schema_link"

    @staticmethod
    def after_link(state: AgentState) -> str:
        return "done" if state.get("gave_up") else "generate_sql"

    @staticmethod
    def after_validate(state: AgentState) -> str:
        if state.get("gave_up") or state.get("sql_valid"):
            return "done"
        return "fix_sql"
