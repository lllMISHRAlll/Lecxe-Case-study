"""PO subgraph: load_draft -> (extract | choose | confirm | cancel) -> ask or confirm -> save."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agents.deps import GraphDeps
from app.agents.po_flow.nodes import PONodes
from app.agents.state import AgentState
from app.agents.untraced import untraced


def build_po_flow(deps: GraphDeps):
    nodes = PONodes(deps)
    graph = StateGraph(AgentState)
    for name in ("load_draft", "extract_slots", "choose", "review_draft", "ask_choice",
                 "ask_next_slot", "show_confirmation", "save_draft", "insert_po", "cancel",
                 "no_draft"):
        graph.add_node(name, getattr(nodes, name))

    graph.add_edge(START, "load_draft")
    graph.add_conditional_edges("load_draft", untraced(nodes.action), {
        "extract": "extract_slots", "choose": "choose", "confirm": "insert_po",
        "cancel": "cancel", "no_draft": "no_draft"})
    graph.add_edge("extract_slots", "review_draft")
    graph.add_edge("choose", "review_draft")
    graph.add_conditional_edges("review_draft", untraced(nodes.after_review),
                                ["ask_choice", "ask_next_slot", "show_confirmation"])
    for asking in ("ask_choice", "ask_next_slot", "show_confirmation"):
        graph.add_edge(asking, "save_draft")
    graph.add_edge("save_draft", END)
    for final in ("insert_po", "cancel", "no_draft"):
        graph.add_edge(final, END)
    return graph.compile(name="po_flow")
