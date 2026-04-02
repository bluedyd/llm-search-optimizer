import os
from tavily import TavilyClient

_client = None


def get_tavily_client() -> TavilyClient:
    global _client
    if _client is None:
        _client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
    return _client


def search_reddit(query: str, max_results: int = 10) -> list[dict]:
    """Reddit 한정으로 Tavily 검색"""
    client = get_tavily_client()
    response = client.search(
        query=f"site:reddit.com {query}",
        max_results=max_results,
        search_depth="advanced",
    )
    return [
        {
            "title": r.get("title", ""),
            "body": r.get("content", ""),
            "url": r.get("url", ""),
            "score": r.get("score", 0.0),
        }
        for r in response.get("results", [])
    ]
