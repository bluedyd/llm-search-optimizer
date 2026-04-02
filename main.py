import asyncio
from dotenv import load_dotenv

load_dotenv()

from agent.graph import app


async def run(user_query: str):
    initial_state = {
        "user_query": user_query,
        "search_queries": [],
        "raw_posts": [],
        "filtered_posts": [],
        "summary": "",
    }

    result = await app.ainvoke(initial_state)

    print(f"\n{'='*60}")
    print(f"검색 의도: {result['user_query']}")
    print(f"검색어: {result['search_queries']}")
    print(f"수집: {len(result['raw_posts'])}개 → 필터 후: {len(result['filtered_posts'])}개")
    print(f"{'='*60}\n")
    print(result["summary"])

    return result


if __name__ == "__main__":
    asyncio.run(run("이 게임을 서비스 종료하겠다는 의견이나 글들"))
