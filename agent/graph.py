from langgraph.graph import StateGraph, END

from .state import AgentState
from .nodes import (
    plan_queries_node,
    dispatch_searches,
    search_node,
    filter_node,
    aggregate_node,
)


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("plan_queries", plan_queries_node)
    graph.add_node("search", search_node)
    graph.add_node("filter", filter_node)
    graph.add_node("aggregate", aggregate_node)

    graph.set_entry_point("plan_queries")
    graph.add_conditional_edges("plan_queries", dispatch_searches, ["search"])
    graph.add_edge("search", "filter")
    graph.add_edge("filter", "aggregate")
    graph.add_edge("aggregate", END)

    return graph.compile()


app = build_graph()
