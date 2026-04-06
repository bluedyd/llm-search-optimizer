import os
import asyncio
import httpx
from datetime import datetime


async def search_reddit_urls(query: str, before_date=None, after_date=None, max_results=20) -> list[str]:
    """Serper.dev로 Reddit 포스트 URL 검색"""
    headers = {
        "X-API-KEY": os.environ["SERPER_API_KEY"],
        "Content-Type": "application/json",
    }
    payload = {"q": f"site:reddit.com {query}", "num": max_results}

    if before_date and after_date:
        b = datetime.strptime(before_date, "%Y-%m-%d")
        a = datetime.strptime(after_date, "%Y-%m-%d")
        payload["tbs"] = f"cdr:1,cd_min:{a.strftime('%m/%d/%Y')},cd_max:{b.strftime('%m/%d/%Y')}"
    elif before_date:
        b = datetime.strptime(before_date, "%Y-%m-%d")
        payload["tbs"] = f"cdr:1,cd_max:{b.strftime('%m/%d/%Y')}"
    elif after_date:
        a = datetime.strptime(after_date, "%Y-%m-%d")
        payload["tbs"] = f"cdr:1,cd_min:{a.strftime('%m/%d/%Y')}"

    async with httpx.AsyncClient(timeout=15) as client:
        res = await client.post(
            "https://google.serper.dev/search",
            headers=headers,
            json=payload,
        )
        res.raise_for_status()
        data = res.json()

    return [
        item["link"]
        for item in data.get("organic", [])
        if "reddit.com/r/" in item.get("link", "") and "/comments/" in item.get("link", "")
    ]


async def fetch_post_details(url: str):
    """Reddit JSON API로 포스트 본문 + 상위 댓글 가져오기"""
    json_url = url.split("?")[0].rstrip("/") + ".json"

    try:
        async with httpx.AsyncClient(
            headers={"User-Agent": "opinion-collector/1.0"},
            timeout=15,
            follow_redirects=True,
        ) as client:
            res = await client.get(json_url, params={"limit": 20, "sort": "top"})
            if res.status_code == 429:
                await asyncio.sleep(2)
                res = await client.get(json_url, params={"limit": 20, "sort": "top"})
            if res.status_code != 200:
                print(f"[fetch] {res.status_code} {url}")
                return None
            data = res.json()

        post = data[0]["data"]["children"][0]["data"]
        comments_raw = data[1]["data"]["children"]

        top_comments = [
            {"body": c["data"].get("body", "")[:200], "score": c["data"].get("score", 0)}
            for c in comments_raw
            if c.get("kind") == "t1"
        ]

        return {
            "title": post.get("title", ""),
            "url": url,
            "score": post.get("score", 0),
            "num_comments": post.get("num_comments", 0),
            "body": post.get("selftext", "")[:300],
            "subreddit": post.get("subreddit", ""),
            "created_at": datetime.utcfromtimestamp(post.get("created_utc", 0)).strftime("%Y-%m-%d"),
            "top_comments": top_comments[:10],
        }
    except Exception as e:
        print(f"[fetch] 실패 {url}: {e}")
        return None
