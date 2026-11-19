"""OBS-08: the LangSmith tree reads like the architecture.

Agents (the turn, the SQL agent, the PO agent) hold their steps directly, steps that act on
the database are typed as tools, routers add no runs, and every run says what it is.
"""

from unittest.mock import MagicMock

import pytest

from app.agents.graph import build_graph
from app.agents.po_flow.graph import build_po_flow
from app.agents.sql_agent.graph import build_sql_agent
from app.llm.tasks import Task
from app.observability.trace_shape import AGENTS, NODES, TOOLS, ShapedTracer
from tests.graph.conftest import BO, PM, base_script, run
from tests.graph.test_graph_paths import GOOD_SQL, analytics

ROUTERS = {"_after_guard", "_by_intent", "_after_sql_agent", "_after_execute",
           "_after_permission", "entry", "after_link", "after_validate", "action",
           "after_review"}


class Capture:
    """A real LangChainTracer subclass whose LangSmith client is a mock."""

    def __init__(self):
        self.client = MagicMock()
        self.tracer = ShapedTracer(client=self.client, project_name="test")

    def created(self) -> dict:
        self.tracer.wait_for_futures()
        return {c.kwargs["id"]: c.kwargs for c in self.client.create_run.call_args_list}

    def updated_ids(self) -> set:
        return {str(c.kwargs["run_id"]) for c in self.client.update_run.call_args_list}


@pytest.fixture
def traced(make_service):
    def factory(script):
        service, _, _ = make_service(script)
        capture = Capture()
        service.tracing.enabled = True
        service.tracing.tracer_factory = lambda metadata: capture.tracer
        return service, capture

    return factory


def by_name(runs: dict) -> dict:
    return {r["name"]: r for r in runs.values()}


def parent_name(runs: dict, run: dict) -> str | None:
    parent = runs.get(run.get("parent_run_id"))
    return parent["name"] if parent else None


def test_sql_agent_steps_nest_directly_under_the_agent(traced):
    service, capture = traced(analytics(**{Task.GENERATE_SQL: [GOOD_SQL]}))
    run(service, BO, message="How many POs does each vendor have?")

    runs = capture.created()
    names = [r["name"] for r in runs.values()]
    named = by_name(runs)
    assert names.count("sql_agent") == 1
    assert "LangGraph" not in names
    assert parent_name(runs, named["sql_agent"]) == "chat_turn"
    for step in ("schema_link", "generate_sql", "validate_sql"):
        assert parent_name(runs, named[step]) == "sql_agent"
    assert parent_name(runs, named["execute_sql"]) == "chat_turn"


def test_routers_add_no_runs(traced):
    service, capture = traced(analytics(**{Task.GENERATE_SQL: [GOOD_SQL]}))
    run(service, BO, message="How many POs does each vendor have?")

    assert not ROUTERS & {r["name"] for r in capture.created().values()}


def test_every_run_is_typed_and_tagged_by_kind(traced):
    service, capture = traced(analytics(**{Task.GENERATE_SQL: [GOOD_SQL]}))
    run(service, BO, message="How many POs does each vendor have?")

    named = by_name(capture.created())
    for agent in ("chat_turn", "sql_agent"):
        assert named[agent]["run_type"] == "chain"
        assert "agent" in named[agent]["tags"]
    for tool in ("execute_sql", "validate_sql", "save_history"):
        assert named[tool]["run_type"] == "tool"
        assert "tool" in named[tool]["tags"]
    for node in ("guard_input", "route_intent", "schema_link", "write_answer"):
        assert named[node]["run_type"] == "chain"
        assert "node" in named[node]["tags"]
    assert named["execute_sql"]["extra"]["metadata"]["kind"] == "tool"


def test_child_runs_drop_repeated_and_internal_tags(traced):
    service, capture = traced(analytics(**{Task.GENERATE_SQL: [GOOD_SQL]}))
    run(service, BO, message="How many POs does each vendor have?")

    runs = capture.created()
    root = by_name(runs)["chat_turn"]
    assert "role:business_owner" in root["tags"]
    for r in runs.values():
        if r is root:
            continue
        assert not [t for t in r["tags"] if t.startswith(("role:", "env:", "seq:", "graph:"))]


def test_every_shown_run_is_completed_and_merged_runs_are_never_sent(traced):
    service, capture = traced(analytics(**{Task.GENERATE_SQL: [GOOD_SQL]}))
    run(service, BO, message="How many POs does each vendor have?")

    created = {str(i) for i in capture.created()}
    assert capture.updated_ids() == created


def test_po_agent_steps_nest_under_the_po_agent(traced):
    service, capture = traced(base_script(**{
        Task.PO_EXTRACT: [{"vendor": "Summit Engineering", "lines": [{"item": "MS Tube 25x40"}]}],
        Task.ROUTE: lambda s, u: {"intent": "raise_po", "confidence": 0.9, "reason": ""},
    }))
    run(service, PM, message="Raise a PO for MS Tube 25x40 from Summit Engineering")

    runs = capture.created()
    named = by_name(runs)
    assert [r["name"] for r in runs.values()].count("po_flow") == 1
    assert parent_name(runs, named["po_flow"]) == "chat_turn"
    for step in ("load_draft", "extract_slots", "review_draft", "save_draft"):
        assert parent_name(runs, named[step]) == "po_flow"
    assert named["load_draft"]["run_type"] == "tool"
    assert "agent" in named["po_flow"]["tags"]


def test_every_graph_node_has_a_kind():
    deps = MagicMock()
    names = set()
    for graph in (build_graph(deps), build_sql_agent(deps), build_po_flow(deps)):
        names |= set(graph.nodes) - {"__start__"}
    assert names - (AGENTS | TOOLS | NODES) == set()
    assert not (AGENTS & TOOLS) and not (TOOLS & NODES) and not (AGENTS & NODES)
