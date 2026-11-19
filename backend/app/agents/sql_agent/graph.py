"""SQL agent subgraph: schema_link -> generate_sql -> validate_sql <-> fix_sql."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agents.deps import GraphDeps
from app.agents.sql_agent.nodes import SqlAgentNodes
from app.agents.state import AgentState
from app.agents.untraced import untraced


def build_sql_agent(deps: GraphDeps):
    nodes = SqlAgentNodes(deps)
    graph = StateGraph(AgentState)
    graph.add_node("schema_link", nodes.schema_link)
    graph.add_node("generate_sql", nodes.generate_sql)
    graph.add_node("validate_sql", nodes.validate_sql)
    graph.add_node("fix_sql", nodes.fix_sql)

    graph.add_conditional_edges(START, untraced(nodes.entry), ["schema_link", "fix_sql"])
    graph.add_conditional_edges("schema_link", untraced(nodes.after_link),
                                {"generate_sql": "generate_sql", "done": END})
    graph.add_edge("generate_sql", "validate_sql")
    graph.add_conditional_edges("validate_sql", untraced(nodes.after_validate),
                                {"fix_sql": "fix_sql", "done": END})
    graph.add_edge("fix_sql", "validate_sql")
    return graph.compile(name="sql_agent")
