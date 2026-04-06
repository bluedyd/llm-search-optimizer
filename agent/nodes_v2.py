import asyncio
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import Send

from .state_v2 import AgentStateV2
from .tools import search_reddit_urls, fetch_post_details
from .nodes import llm, analyze_node, plan_queries_node  # 재사용


# ── Structured Output ─────────────────────────────────────────────────────────

class RelevanceResult(BaseModel):
    relevant_urls: list[str]  # 관련 있는 포스트 URL 목록

class GapAnalysis(BaseModel):
    is_sufficient: bool
    reasoning: str
    new_queries: list[str]


# ── 1. Plan Queries (v1과 동일, 재사용) ──────────────────────────────────────

async def plan_queries_node_v2(state: AgentStateV2) -> dict:
    result = await plan_queries_node(state)
    return {
        "search_queries": result["search_queries"],
        "all_queries_used": result["search_queries"],
        "iteration_count": 0,
        "urls_count_before": 0,
    }


# ── 2. Search (병렬) ──────────────────────────────────────────────────────────

def dispatch_searches_v2(state: AgentStateV2) -> list[Send]:
    return [Send("search", {**state, "_query": q}) for q in state["search_queries"]]


async def search_node_v2(state: dict) -> dict:
    urls = await search_reddit_urls(
        state["_query"],
        before_date=state.get("before_date"),
        after_date=state.get("after_date"),
    )
    return {"post_urls": urls}


# ── 3. Fetch Posts (incremental) ─────────────────────────────────────────────

async def fetch_posts_node_v2(state: AgentStateV2) -> dict:
    fetched_urls = {p["url"] for p in state.get("posts", [])}

    seen: set[str] = set()
    new_urls: list[str] = []
    for url in state["post_urls"]:
        if url not in fetched_urls and url not in seen:
            seen.add(url)
            new_urls.append(url)

    sem = asyncio.Semaphore(3)

    async def fetch_with_limit(url):
        async with sem:
            await asyncio.sleep(1)
            return await fetch_post_details(url)

    results = await asyncio.gather(*[fetch_with_limit(u) for u in new_urls])
    new_posts = [p for p in results if p is not None]

    if state.get("before_date"):
        new_posts = [p for p in new_posts if p["created_at"] < state["before_date"]]
    if state.get("after_date"):
        new_posts = [p for p in new_posts if p["created_at"] > state["after_date"]]

    return {"posts": state.get("posts", []) + new_posts}


# ── 4. Relevance Filter ──────────────────────────────────────────────────────

async def filter_posts_node(state: AgentStateV2) -> dict:
    """포스트 제목+본문을 보고 user_query와 관련 없는 노이즈 제거."""
    posts = state.get("posts", [])
    if not posts:
        return {}

    post_lines = "\n".join(
        f"{p['url']} | [r/{p['subreddit']}] {p['title']} | {p['body'][:80]}"
        for p in posts
    )

    result = await llm.with_structured_output(RelevanceResult).ainvoke([
        SystemMessage(content=(
            "You are a relevance filter for Reddit research. "
            "Given a research intent and a list of posts, return only the URLs of posts "
            "that are DIRECTLY relevant to the intent. "
            "Exclude posts that only tangentially mention keywords but are about unrelated topics."
        )),
        HumanMessage(content=(
            f"Research intent: {state['user_query']}\n\n"
            f"Posts (url | subreddit + title | body snippet):\n{post_lines}"
        )),
    ])

    relevant_url_set = set(result.relevant_urls)
    filtered = [p for p in posts if p["url"] in relevant_url_set]
    return {"posts": filtered}


# ── 5. Gap Analysis (FLARE 핵심) ─────────────────────────────────────────────

async def gap_analysis_node(state: AgentStateV2) -> dict:
    posts = state.get("posts", [])
    titles = [f"[r/{p['subreddit']}] {p['title']}" for p in posts]

    result = await llm.with_structured_output(GapAnalysis).ainvoke([
        SystemMessage(content=(
            "You are a research gap analyzer. "
            "Given a research intent and collected Reddit posts so far, "
            "decide whether the collection sufficiently covers the intent. "
            "If there are clearly uncovered aspects, generate 2-3 new search queries to fill those gaps. "
            "Do NOT generate queries that paraphrase already-used queries. "
            "Set is_sufficient=True if coverage is good enough or no meaningful gaps remain."
        )),
        HumanMessage(content=(
            f"Research intent: {state['user_query']}\n"
            f"Queries already used: {state['all_queries_used']}\n"
            f"Collected posts ({len(titles)}):\n" + "\n".join(titles)
        )),
    ])

    iteration = state.get("iteration_count", 0) + 1
    max_iter = state.get("max_iterations", 3)

    if result.is_sufficient or iteration >= max_iter:
        return {
            "iteration_count": iteration,
            "is_sufficient": True,
        }

    return {
        "iteration_count": iteration,
        "is_sufficient": False,
        "search_queries": result.new_queries,
        "all_queries_used": result.new_queries,
        "urls_count_before": len(state["post_urls"]),
    }


def route_after_gap_analysis(state: AgentStateV2):
    if state["is_sufficient"]:
        return "analyze"
    return [Send("search", {**state, "_query": q}) for q in state["search_queries"]]
