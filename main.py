import asyncio
import json
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from agent.graph import app
from agent.state import initial_state
from agent.graph_v2 import app_v2
from agent.state_v2 import initial_state_v2


async def run(
    user_query: str,
    before_date: str = None,
    max_iterations: int = 3,
    after_date: str = None,
    version: int = 1,
):
    print(f"\n{'='*60}")
    print(f"[v{version}] {user_query}")
    print(f"{'='*60}")

    if version == 1:
        result = await app.ainvoke(initial_state(user_query, before_date, after_date))
        unique_urls = list(dict.fromkeys(result["post_urls"]))
        print(f"검색어: {result['search_queries']}")
        print(f"URL 수집: {len(unique_urls)}개 (중복 제거 전: {len(result['post_urls'])}개) → 크롤링: {len(result['posts'])}개")
        print(f"{'='*60}\n")
        print(result["analysis"])
        payload = {
            "version": 1,
            "user_query": result["user_query"],
            "before_date": before_date,
            "after_date": after_date,
            "search_queries": result["search_queries"],
            "post_urls": unique_urls,
            "posts": result["posts"],
            "analysis": result["analysis"],
        }

    else:
        result = await app_v2.ainvoke(initial_state_v2(user_query, before_date, after_date, max_iterations))
        unique_urls = list(dict.fromkeys(result["post_urls"]))
        print(f"총 이터레이션: {result['iteration_count']}")
        print(f"사용된 쿼리 ({len(result['all_queries_used'])}개): {result['all_queries_used']}")
        print(f"URL 수집: {len(unique_urls)}개 (중복 제거 전: {len(result['post_urls'])}개) → 필터 후: {len(result['posts'])}개")
        print(f"{'='*60}\n")
        print(result["analysis"])
        payload = {
            "version": 2,
            "user_query": result["user_query"],
            "before_date": before_date,
            "after_date": after_date,
            "iterations": result["iteration_count"],
            "all_queries_used": result["all_queries_used"],
            "post_urls": unique_urls,
            "posts": result["posts"],
            "analysis": result["analysis"],
        }

    os.makedirs("exps", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = f"exps/{timestamp}_v{version}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"\n저장 완료: {filepath}")

    return result


if __name__ == "__main__":
    asyncio.run(run(
        user_query="Solo Leveling fans demand for a video game adaptation - do fans want Solo Leveling as a game",
        before_date="2022-01-01",
        version=2,
        max_iterations=3,
    ))