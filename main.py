import asyncio
import json
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from agent.graph import app
from agent.state import initial_state


async def run(user_query: str, before_date: str = None, after_date: str = None):
    result = await app.ainvoke(initial_state(user_query, before_date, after_date))

    print(f"\n{'='*60}")
    print(f"검색 의도: {result['user_query']}")
    print(f"검색어: {result['search_queries']}")
    print(f"URL 수집: {len(result['post_urls'])}개 → 상세 크롤링: {len(result['posts'])}개")
    print(f"{'='*60}\n")
    print(result["analysis"])

    os.makedirs("exps", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = f"exps/{timestamp}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump({
            "user_query": result["user_query"],
            "before_date": before_date,
            "after_date": after_date,
            "search_queries": result["search_queries"],
            "post_urls": result["post_urls"],
            "posts": result["posts"],
            "analysis": result["analysis"],
        }, f, ensure_ascii=False, indent=2)
    print(f"\n저장 완료: {filepath}")

    return result


if __name__ == "__main__":
    asyncio.run(run(user_query="Solo Leveling IP를 게임으로 만들어달라는 팬들의 니즈나 수요가 있는지",
                    before_date="2023-01-01"))
