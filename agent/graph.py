from langgraph.graph import StateGraph, END

from .state import AgentState
from .nodes import (
    plan_queries_node,
    dispatch_searches,
    search_node,
    fetch_posts_node,
    analyze_node,
)


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("plan_queries", plan_queries_node)
    graph.add_node("search", search_node)
    graph.add_node("fetch_posts", fetch_posts_node)
    graph.add_node("analyze", analyze_node)

    graph.set_entry_point("plan_queries")
    graph.add_conditional_edges("plan_queries", dispatch_searches, ["search"])
    graph.add_edge("search", "fetch_posts")
    graph.add_edge("fetch_posts", "analyze")
    graph.add_edge("analyze", END)

    return graph.compile()


app = build_graph()
