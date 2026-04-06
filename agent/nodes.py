import json
import re
import asyncio
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import Send

from .state import AgentState
from .tools import search_reddit_urls, fetch_post_details

llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)


def parse_json(text: str):
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        return json.loads(match.group(1).strip())
    match = re.search(r"\[[\s\S]*\]", text)
    if match:
        return json.loads(match.group(0))
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        return json.loads(match.group(0))
    raise ValueError(f"No JSON found: {text[:200]}")


# ── 1. Query Planner ─────────────────────────────────────────────────────────

async def plan_queries_node(state: AgentState) -> dict:
    response = await llm.ainvoke([
        SystemMessage(content=(
            "You are a search query generator for Reddit research. "
            "Generate 3-5 effective English search queries that find Reddit posts "
            "where fans EXPRESS DESIRE, wishful thinking, or demand — "
            "e.g. 'X needs a game', 'I wish X had a game', 'when is X getting a game'. "
            "Focus on capturing fan demand signals, not reviews or news. "
            'Return JSON: {"queries": ["query1", "query2", ...]}'
        )),
        HumanMessage(content=f"User request: {state['user_query']}"),
    ])
    result = parse_json(response.content)
    queries = result if isinstance(result, list) else result.get("queries", [])
    return {"search_queries": queries}


# ── 2. Search (쿼리별 병렬) ───────────────────────────────────────────────────

def dispatch_searches(state: AgentState) -> list[Send]:
    return [Send("search", {**state, "_query": q}) for q in state["search_queries"]]


async def search_node(state: dict) -> dict:
    urls = await search_reddit_urls(
        state["_query"],
        before_date=state.get("before_date"),
        after_date=state.get("after_date"),
    )
    return {"post_urls": urls}


# ── 3. Fetch Posts (병렬 + Semaphore) ────────────────────────────────────────

async def fetch_posts_node(state: AgentState) -> dict:
    # 중복 URL 제거
    seen = set()
    unique_urls = []
    for url in state["post_urls"]:
        if url not in seen:
            seen.add(url)
            unique_urls.append(url)

    # 최대 3개 동시 요청으로 Reddit rate limit 회피
    sem = asyncio.Semaphore(3)

    async def fetch_with_limit(url):
        async with sem:
            await asyncio.sleep(1)
            return await fetch_post_details(url)

    results = await asyncio.gather(*[fetch_with_limit(u) for u in unique_urls[:10]])
    posts = [p for p in results if p is not None]

    # before_date 기준 후처리 필터링 (Serper 날짜 필터 보완)
    if state.get("before_date"):
        posts = [p for p in posts if p["created_at"] < state["before_date"]]
    if state.get("after_date"):
        posts = [p for p in posts if p["created_at"] > state["after_date"]]

    return {"posts": posts}


# ── 4. Analyze ────────────────────────────────────────────────────────────────

async def analyze_node(state: AgentState) -> dict:
    if not state["posts"]:
        return {"analysis": "관련 포스트를 찾지 못했습니다."}

    top_posts = sorted(state["posts"], key=lambda x: -x["score"])[:10]

    posts_text = ""
    for p in top_posts:
        comments_text = "\n".join(
            f"  └ (👍{c['score']}) {c['body']}"
            for c in sorted(p["top_comments"], key=lambda x: -x["score"])[:5]
        )
        posts_text += (
            f"\n### [{p['created_at']}] {p['title']}"
            f"\n r/{p['subreddit']} | 추천수: {p['score']} | 댓글: {p['num_comments']}"
            f"\n 본문: {p['body'][:150]}"
            f"\n 상위 댓글:\n{comments_text}\n"
        )

    response = await llm.ainvoke([
        SystemMessage(content=(
            "You are an opinion analyst. Analyze Reddit posts and comments in Korean. "
            "Structure your response:\n"
            "1) 전체 반응 요약 (긍정/부정/중립 비율 추정)\n"
            "2) 주요 의견 분류 (가장 많이 동의받은 의견 위주)\n"
            "3) 주목할 포스트 top 3 (추천수 + 댓글 반응 기준)\n"
            "4) 결론: 이 주제에 대한 커뮤니티 전반적 온도"
        )),
        HumanMessage(content=(
            f"검색 의도: {state['user_query']}\n"
            f"수집된 포스트 ({len(state['posts'])}개):\n{posts_text}"
        )),
    ])

    return {"analysis": response.content}
