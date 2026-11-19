"""The orchestrator: one LangGraph main graph with the SQL-agent and PO subgraphs.

    preprocess -> guard_input -> rewrite_followup -> route_intent
      button      -> load_canned_sql -> execute_sql
      analytics   -> sql_agent -> execute_sql (runtime error -> sql_agent fix, max 3 tries)
      raise_po    -> check_po_permission -> po_flow
      chit_chat   -> chat ; unclear -> ask_clarify
    execute_sql -> reduce_results -> [choose_chart | write_answer -> check_answer]
    every path ends in save_history.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agents.deps import GraphDeps
from app.agents.nodes.main import MAX_ATTEMPTS, MainNodes
from app.agents.po_flow.graph import build_po_flow
from app.agents.sql_agent.graph import build_sql_agent
from app.agents.state import AgentState
from app.agents.untraced import untraced


def _after_guard(state: AgentState) -> str:
    return "reply" if state.get("reply") else "rewrite_followup"


def _by_intent(state: AgentState) -> str:
    return {"canned": "load_canned_sql", "analytics": "sql_agent",
            "raise_po": "check_po_permission", "chit_chat": "chat",
            "clarify": "ask_clarify"}[state["intent"]]


def _after_sql_agent(state: AgentState) -> str:
    return "reply" if state.get("gave_up") else "execute_sql"


def _after_execute(state: AgentState) -> str:
    if state.get("result") is not None:
        return "reduce_results"
    if state.get("reply"):
        return "reply"
    return "sql_agent" if state.get("attempts", 1) < MAX_ATTEMPTS else "reply"


def _after_permission(state: AgentState) -> str:
    return "reply" if state.get("reply") else "po_flow"


def build_graph(deps: GraphDeps):
    nodes = MainNodes(deps)
    graph = StateGraph(AgentState)
    for name in ("preprocess", "guard_input", "rewrite_followup", "route_intent",
                 "load_canned_sql", "execute_sql", "reduce_results", "choose_chart",
                 "write_answer", "check_answer", "check_po_permission", "ask_clarify", "chat",
                 "reply", "save_history"):
        graph.add_node(name, getattr(nodes, name))
    graph.add_node("sql_agent", build_sql_agent(deps))
    graph.add_node("po_flow", build_po_flow(deps))

    graph.add_edge(START, "preprocess")
    graph.add_edge("preprocess", "guard_input")
    graph.add_conditional_edges("guard_input", untraced(_after_guard),
                                ["reply", "rewrite_followup"])
    graph.add_edge("rewrite_followup", "route_intent")
    graph.add_conditional_edges("route_intent", untraced(_by_intent), [
        "load_canned_sql", "sql_agent", "check_po_permission", "chat", "ask_clarify"])
    graph.add_edge("load_canned_sql", "execute_sql")
    graph.add_conditional_edges("sql_agent", untraced(_after_sql_agent), ["reply", "execute_sql"])
    graph.add_conditional_edges("execute_sql", untraced(_after_execute),
                                ["reduce_results", "sql_agent", "reply"])
    graph.add_edge("reduce_results", "choose_chart")
    graph.add_edge("reduce_results", "write_answer")
    graph.add_edge("write_answer", "check_answer")
    graph.add_edge(["choose_chart", "check_answer"], "save_history")
    graph.add_conditional_edges("check_po_permission", untraced(_after_permission),
                                ["reply", "po_flow"])
    graph.add_edge("po_flow", "reply")
    graph.add_edge("chat", "reply")
    graph.add_edge("ask_clarify", "reply")
    graph.add_edge("reply", "save_history")
    graph.add_edge("save_history", END)
    return graph.compile()
