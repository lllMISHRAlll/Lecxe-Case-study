"""Makes the LangSmith tree read like the architecture.

    chat_turn            agent   the orchestrator (root run)
    ├─ guard_input       node
    │  └─ llm.guard      llm
    ├─ sql_agent         agent   SQL subgraph; its steps sit directly under it
    │  ├─ schema_link    node
    │  └─ validate_sql   tool
    ├─ execute_sql       tool
    └─ save_history      tool

* Every run gets a kind: `agent`, `tool`, `llm` or `node`, as a tag and as `metadata.kind`.
  Tools are also sent with run_type "tool", so LangSmith shows them with the tool icon.
* LangGraph traces a subgraph twice (the node, then the compiled graph inside it). The inner
  run is never sent and its children are re-parented onto the node, so the agent is one row.
* Child runs drop tags that only add noise there: LangGraph's `graph:step:N`/`seq:step:N`, and
  the root's `role:`/`env:` tags, which LangChain copies onto every child. The root keeps them.
* Routers are not traced at all; see `app.agents.untraced`.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from langchain_core.tracers.langchain import LangChainTracer
from langchain_core.tracers.schemas import Run

AGENTS = frozenset({"chat_turn", "sql_agent", "po_flow"})
# Steps that act on the database or apply fixed rules, with no model call.
TOOLS = frozenset({
    "load_canned_sql", "execute_sql", "reduce_results", "check_po_permission", "save_history",
    "validate_sql", "load_draft", "save_draft", "insert_po", "cancel",
})
# Steps that call a model or decide what to say next.
NODES = frozenset({
    "preprocess", "guard_input", "rewrite_followup", "route_intent", "choose_chart",
    "write_answer", "check_answer", "ask_clarify", "chat", "reply",
    "schema_link", "generate_sql", "fix_sql",
    "extract_slots", "choose", "review_draft", "ask_choice", "ask_next_slot",
    "show_confirmation", "no_draft",
})
_INTERNAL_TAGS = ("graph:step:", "seq:step:")
_ROOT_ONLY_TAGS = ("role:", "env:")


def kind_of(run: Run) -> str | None:
    if run.run_type == "llm" or run.name.startswith("llm."):
        return "llm"
    if run.name in AGENTS:
        return "agent"
    if run.name in TOOLS:
        return "tool"
    if run.name in NODES:
        return "node"
    return None


def shape(run: Run, *, is_root: bool) -> None:
    tags = [t for t in run.tags or [] if not t.startswith(_INTERNAL_TAGS)
            and (is_root or not t.startswith(_ROOT_ONLY_TAGS))]
    kind = kind_of(run)
    if kind is not None:
        if kind == "tool":
            run.run_type = "tool"
        if kind not in tags:
            tags.append(kind)
        extra = dict(run.extra or {})
        extra["metadata"] = {**(extra.get("metadata") or {}), "kind": kind}
        run.extra = extra
    run.tags = tags


class ShapedTracer(LangChainTracer):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._merged: set[UUID] = set()

    def _parent(self, run: Run) -> Run | None:
        return self.run_map.get(str(run.parent_run_id)) if run.parent_run_id else None

    def _start_trace(self, run: Run) -> None:
        parent = self._parent(run)
        while parent is not None and parent.id in self._merged:
            run.parent_run_id = parent.parent_run_id
            parent = self._parent(run)
        if parent is not None and parent.name in AGENTS and run.name == parent.name:
            self._merged.add(run.id)  # the compiled subgraph inside its own node
        shape(run, is_root=parent is None)
        super()._start_trace(run)

    def _on_chain_start(self, run: Run) -> None:
        if run.id not in self._merged:
            super()._on_chain_start(run)

    def _on_chain_end(self, run: Run) -> None:
        if run.id not in self._merged:
            super()._on_chain_end(run)

    def _on_chain_error(self, run: Run) -> None:
        if run.id not in self._merged:
            super()._on_chain_error(run)
