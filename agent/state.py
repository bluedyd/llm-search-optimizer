from typing import TypedDict, Annotated, Optional
import operator


class Comment(TypedDict):
    body: str
    score: int


class PostDetail(TypedDict):
    title: str
    url: str
    score: int           # 포스트 추천수
    num_comments: int
    body: str
    subreddit: str
    created_at: str
    top_comments: list   # Comment 목록


class AgentState(TypedDict):
    user_query: str
    before_date: Optional[str]
    search_queries: list[str]
    post_urls: Annotated[list[str], operator.add]  # 병렬 검색 결과 누적
    posts: list[PostDetail]                        # 상세 크롤링 결과
    analysis: str                                  # 최종 분석
