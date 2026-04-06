from langgraph.graph import StateGraph, END

from .state_v2 import AgentStateV2
from .nodes import analyze_node
from .nodes_v2 import (
    plan_queries_node_v2,
    dispatch_searches_v2,
    search_node_v2,
    fetch_posts_node_v2,
    filter_posts_node,
    gap_analysis_node,
    route_after_gap_analysis,
)


def build_graph_v2():
    graph = StateGraph(AgentStateV2)

    graph.add_node("plan_queries", plan_queries_node_v2)
    graph.add_node("search", search_node_v2)
    graph.add_node("fetch_posts", fetch_posts_node_v2)
    graph.add_node("filter_posts", filter_posts_node)
    graph.add_node("gap_analysis", gap_analysis_node)
    graph.add_node("analyze", analyze_node)

    graph.set_entry_point("plan_queries")
    graph.add_conditional_edges("plan_queries", dispatch_searches_v2, ["search"])
    graph.add_edge("search", "fetch_posts")
    graph.add_edge("fetch_posts", "filter_posts")
    graph.add_edge("filter_posts", "gap_analysis")
    graph.add_conditional_edges(
        "gap_analysis",
        route_after_gap_analysis,
        ["analyze", "search"],
    )
    graph.add_edge("analyze", END)

    return graph.compile()


app_v2 = build_graph_v2()
