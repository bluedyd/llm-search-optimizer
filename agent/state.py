from typing import TypedDict, Annotated
import operator


class Post(TypedDict):
    title: str
    body: str
    url: str
    score: float  # Tavily relevance score


class AgentState(TypedDict):
    user_query: str                              # 사용자 자연어 요청
    search_queries: list[str]                    # 생성된 검색어들
    raw_posts: Annotated[list[Post], operator.add]  # 수집된 원본 결과 (병렬 누적)
    filtered_posts: list[Post]                   # 관련성 통과한 결과
    summary: str                                 # 최종 요약
