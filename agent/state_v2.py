from typing import TypedDict, Annotated, Optional
import operator

from .state import PostDetail


class AgentStateV2(TypedDict):
    user_query: str
    before_date: Optional[str]
    after_date: Optional[str]
    search_queries: list[str]
    all_queries_used: Annotated[list[str], operator.add]
    post_urls: Annotated[list[str], operator.add]
    urls_count_before: int
    posts: list[PostDetail]
    analysis: str
    iteration_count: int
    max_iterations: int
    is_sufficient: bool


def initial_state_v2(
    user_query: str,
    before_date: str = None,
    after_date: str = None,
    max_iterations: int = 3,
) -> AgentStateV2:
    return {
        "user_query": user_query,
        "before_date": before_date,
        "after_date": after_date,
        "search_queries": [],
        "all_queries_used": [],
        "post_urls": [],
        "urls_count_before": 0,
        "posts": [],
        "analysis": "",
        "iteration_count": 0,
        "max_iterations": max_iterations,
        "is_sufficient": False,
    }
