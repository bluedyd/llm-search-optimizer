import json
import re
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import Send

from .state import AgentState
from .tools import search_reddit

llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)


def parse_json(text: str) -> dict:
    """텍스트에서 JSON 객체 추출 후 파싱"""
    text = text.strip()
    # ```json ... ``` 코드블록 우선 시도
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        return json.loads(match.group(1).strip())
    # 중괄호로 감싸진 JSON 객체 추출
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        return json.loads(match.group(0))
    raise ValueError(f"No JSON found in response: {text[:200]}")


# ── 1. Query Planner ─────────────────────────────────────────────────────────

async def plan_queries_node(state: AgentState) -> dict:
    """자연어 요청 → 검색어 목록으로 변환"""
    response = await llm.ainvoke([
        SystemMessage(content=(
            "You are a search query generator for Reddit opinion research. "
            "Convert the user's request into 3-5 effective English search queries. "
            "Return JSON: {\"queries\": [\"query1\", \"query2\", ...]}"
        )),
        HumanMessage(content=f"User request: {state['user_query']}"),
    ])

    result = parse_json(response.content)
    return {"search_queries": result.get("queries", [])}


# ── 2. Search (쿼리별 병렬 실행) ─────────────────────────────────────────────

def dispatch_searches(state: AgentState) -> list[Send]:
    return [Send("search", {**state, "_query": q}) for q in state["search_queries"]]


def search_node(state: dict) -> dict:
    posts = search_reddit(state["_query"])
    return {"raw_posts": posts}


# ── 3. Filter ────────────────────────────────────────────────────────────────

async def filter_node(state: AgentState) -> dict:
    if not state["raw_posts"]:
        return {"filtered_posts": []}

    # 중복 URL 제거
    seen = set()
    unique_posts = []
    for post in state["raw_posts"]:
        if post["url"] not in seen:
            seen.add(post["url"])
            unique_posts.append(post)

    posts_text = "\n\n".join(
        f"[{i}] {p['title']}\n{p['body'][:300]}"
        for i, p in enumerate(unique_posts)
    )

    response = await llm.ainvoke([
        SystemMessage(content=(
            "You are a relevance filter. Given the user's intent and a list of posts, "
            "return indices of genuinely relevant ones. "
            "Return JSON: {\"relevant_indices\": [0, 2, 5, ...]}"
        )),
        HumanMessage(content=f"User intent: {state['user_query']}\n\nPosts:\n{posts_text}"),
    ])

    result = parse_json(response.content)
    indices = result.get("relevant_indices", [])
    return {"filtered_posts": [unique_posts[i] for i in indices if i < len(unique_posts)]}


# ── 4. Aggregate ─────────────────────────────────────────────────────────────

async def aggregate_node(state: AgentState) -> dict:
    if not state["filtered_posts"]:
        return {"summary": "관련 포스트를 찾지 못했습니다."}

    posts_text = "\n\n".join(
        f"- {p['title']}\n  {p['body'][:500]}\n  URL: {p['url']}"
        for p in state["filtered_posts"]
    )

    response = await llm.ainvoke([
        SystemMessage(content=(
            "You are an opinion analyst. Summarize the collected Reddit posts in Korean. "
            "Structure: 1) 전체 요약 2) 주요 의견 분류 3) 주목할 포스트 (top 3)"
        )),
        HumanMessage(content=(
            f"검색 의도: {state['user_query']}\n\n"
            f"수집된 포스트 ({len(state['filtered_posts'])}개):\n{posts_text}"
        )),
    ])

    return {"summary": response.content}
