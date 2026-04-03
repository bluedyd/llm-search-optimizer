from typing import TypedDict, Annotated, Optional
import operator


class Comment(TypedDict):
    body: str
    score: int


class PostDetail(TypedDict):
    title: str
    url: str
    score: int
    num_comments: int
    body: str
    subreddit: str
    created_at: str
    top_comments: list[Comment]


class AgentState(TypedDict):
    user_query: str
    before_date: Optional[str]
    after_date: Optional[str]
    search_queries: list[str]
    post_urls: Annotated[list[str], operator.add]
    posts: list[PostDetail]
    analysis: str


def initial_state(user_query: str, before_date: str = None, after_date: str = None) -> AgentState:
    return {
        "user_query": user_query,
        "before_date": before_date,
        "after_date": after_date,
        "search_queries": [],
        "post_urls": [],
        "posts": [],
        "analysis": "",
    }
