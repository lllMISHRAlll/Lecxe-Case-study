"""Main graph nodes: understand the message, run the query, answer, reply, save."""

from __future__ import annotations

import logging
from typing import Any

from app.agents.deps import GraphDeps
from app.agents.events import emit, step, stream_text
from app.agents.prompts.answer import ANSWER_SYSTEM, ANSWER_USER, CHAT_SYSTEM
from app.agents.state import AgentState
from app.guardrails.answer_check import check_answer_numbers, template_answer
from app.guardrails.preprocess import InputRejectedError, preprocess
from app.llm.tasks import Task
from app.rbac.capabilities import Capability, has_capability
from app.sql.canned import CannedContext, latest_activity
from app.sql.executor import QueryFailedError
from app.viz.chart_builder import build_chart
from app.viz.reducer import reduce_result

log = logging.getLogger(__name__)
MAX_ATTEMPTS = 3

BLOCKED = ("Sorry, I can't help with that. I can answer questions about vendors, purchase "
           "orders, payments, receipts and stock.")
DENIED = ("Only the Procurement Manager can raise purchase orders. I can still help you look "
          "up POs, vendors and stock.")
CLARIFY = ("Could you say a bit more about what you'd like to see? For example: open POs, "
           "spend by vendor, or stock at a warehouse.")
QUERY_FAILED = "Sorry, I couldn't run that query: {error}. Try rephrasing the question."
PO_ACTION_LABELS = {"confirm": "Confirm PO", "cancel": "Cancel PO", "choose": "Chose an option"}


def _rows_event(result) -> dict[str, Any]:
    return {"columns": [{"name": c.name, "type": c.type} for c in result.columns],
            "rows": result.rows, "row_count": result.row_count, "truncated": result.truncated}


class MainNodes:
    def __init__(self, deps: GraphDeps) -> None:
        self.d = deps

    # ------------------------------------------------------------------ understand

    def preprocess(self, state: AgentState) -> dict[str, Any]:
        update: dict[str, Any] = {"payload": {}, "notes": []}
        if state.get("button_id"):
            update["question"] = self.d.registry.get(state["button_id"]).label
        elif state.get("po_action"):
            update["question"] = PO_ACTION_LABELS.get(state["po_action"].get("type", ""), "")
        else:
            try:
                update["question"] = preprocess(state.get("message") or "").text
            except InputRejectedError as exc:
                update |= {"question": "", "reply": str(exc), "reply_mode": "text"}
        step("preprocess", "Read your message")
        return update

    def guard_input(self, state: AgentState) -> dict[str, Any]:
        if state.get("message") and not state.get("reply"):
            verdict = self.d.guard.check(state["question"])
            if not verdict.allowed:
                log.info("Blocked message: %s", verdict.category)
                step("guard_input", "Message blocked")
                return {"reply": BLOCKED, "reply_mode": "text"}
        step("guard_input", "Safety checks passed")
        return {}

    def rewrite_followup(self, state: AgentState) -> dict[str, Any]:
        if not state.get("message"):
            return {}
        question = self.d.rewriter.rewrite(state["question"], state.get("history") or [])
        return {"question": question}

    def route_intent(self, state: AgentState) -> dict[str, Any]:
        has_draft = self.d.history.open_draft(state["conversation_id"]) is not None
        action = (state.get("po_action") or {}).get("type")
        decision = self.d.router.route(state["question"], button_id=state.get("button_id"),
                                       po_action=action, has_open_draft=has_draft)
        step("route_intent", f"Routed to {decision.intent.value.replace('_', ' ')}")
        return {"intent": decision.intent.value, "po_command": decision.po_command}

    # ------------------------------------------------------------------ query

    def load_canned_sql(self, state: AgentState) -> dict[str, Any]:
        query = self.d.registry.get_for(state["user"].role, state["button_id"] or "")
        ctx = CannedContext(today=self.d.clock.today(), fx_usd_inr=self.d.settings.fx_usd_inr)
        emit("sql", {"sql": query.sql.strip(), "source": "button", "attempt": 1})
        step("load_canned_sql", "Loaded the saved query")
        return {"sql": query.sql, "sql_params": query.params(ctx), "sql_source": "button",
                "chart_hint": query.chart, "notes": [n for n in [query.note(ctx)] if n],
                "attempts": 1, "payload": {"sql": {"sql": query.sql.strip(), "source": "button",
                                                   "attempt": 1}}}

    def execute_sql(self, state: AgentState) -> dict[str, Any]:
        try:
            result = self.d.executor.run(state["sql"] or "", state.get("sql_params") or {})
        except QueryFailedError as exc:
            step("execute_sql", "The query failed")
            errors = [*state.get("sql_errors", []), str(exc)]
            can_retry = (state.get("sql_source") != "button"
                         and state.get("attempts", 1) < MAX_ATTEMPTS)
            if can_retry:
                return {"sql_errors": errors, "sql_valid": False, "result": None}
            return {"sql_errors": errors, "result": None, "reply_mode": "text",
                    "reply": QUERY_FAILED.format(error=str(exc).rstrip("."))}
        rows = _rows_event(result)
        emit("rows", rows)
        step("execute_sql", f"Ran the query ({result.row_count} rows)")
        sql_record = {"sql": state["sql"], "source": state.get("sql_source"),
                      "attempt": state.get("attempts", 1)}
        return {"result": result, "payload": {"rows": rows, "sql": sql_record}}

    def reduce_results(self, state: AgentState) -> dict[str, Any]:
        result = state["result"]
        assert result is not None
        notes = list(state.get("notes") or [])
        if "usd" in (state.get("sql") or "").lower() and not notes:
            notes.append(f"USD amounts are converted at ₹{self.d.settings.fx_usd_inr:g} per USD.")
        if result.row_count == 0:
            latest = latest_activity(self.d.executor)
            notes.append(f"Latest PO placed on {latest['po_placed']}; latest stock movement on "
                         f"{latest['stock_movement']}.")
        return {"reduced": reduce_result(result), "notes": notes}

    def choose_chart(self, state: AgentState) -> dict[str, Any]:
        result = state["result"]
        assert result is not None
        decision = self.d.charts.decide(result, state["question"], hint=state.get("chart_hint"))
        spec = build_chart(result, decision, title=state["question"])
        emit("chart", spec)
        step("choose_chart", "Picked a chart" if spec["type"] != "table" else "Table view")
        return {"payload": {"chart": spec}}

    def write_answer(self, state: AgentState) -> dict[str, Any]:
        reduced = state["reduced"]
        assert reduced is not None
        system = ANSWER_SYSTEM.format(role=state["user"].role.label)
        user = ANSWER_USER.format(question=state["question"], summary=reduced.to_prompt(),
                                  notes="\n".join(state.get("notes") or []) or "none")
        parts: list[str] = []
        for token in self.d.llm.stream(Task.ANSWER, system=system, user=user):
            parts.append(token)
            emit("token", {"text": token})
        return {"answer": "".join(parts)}

    def check_answer(self, state: AgentState) -> dict[str, Any]:
        result = state["result"]
        assert result is not None
        context = " ".join([state["question"], *(state.get("notes") or [])])
        check = check_answer_numbers(state.get("answer", ""), result, context)
        if check.ok:
            return {}
        log.info("Answer replaced; unknown numbers %s", check.unknown)
        replacement = template_answer(result)
        emit("answer_replace", {"text": replacement})
        return {"answer": replacement}

    # ------------------------------------------------------------------ replies

    def check_po_permission(self, state: AgentState) -> dict[str, Any]:
        if has_capability(state["user"].role, Capability.PO_CREATE):
            return {}
        step("check_po_permission", "Not allowed for this role")
        return {"reply": DENIED, "reply_mode": "text"}

    def ask_clarify(self, state: AgentState) -> dict[str, Any]:
        return {"reply": CLARIFY, "reply_mode": "text"}

    def reply(self, state: AgentState) -> dict[str, Any]:
        if state.get("reply_mode") == "chat":
            user = state["user"]
            buttons = ", ".join(q.label for q in self.d.registry.for_role(user.role))
            po_line = ("You can also raise purchase orders by describing them."
                       if has_capability(user.role, Capability.PO_CREATE) else "")
            parts = []
            for token in self.d.llm.stream(
                    Task.CHAT_REPLY, user=state["question"],
                    system=CHAT_SYSTEM.format(name=user.name, role=user.role.label,
                                              po_line=po_line, buttons=buttons)):
                parts.append(token)
                emit("token", {"text": token})
            return {"reply": "".join(parts)}
        stream_text(state.get("reply") or "")
        return {}

    def chat(self, state: AgentState) -> dict[str, Any]:
        return {"reply_mode": "chat"}

    def save_history(self, state: AgentState) -> dict[str, Any]:
        text = state.get("answer") or state.get("reply") or ""
        payload = dict(state.get("payload") or {})
        payload["steps"] = state.get("steps") or []
        message_id = self.d.history.add_message(state["conversation_id"], "assistant", text,
                                                payload=payload)
        emit("saved", {"message_id": message_id})
        return {}
