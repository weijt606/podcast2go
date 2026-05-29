"""Web search: query -> {"answer": str, "sources": [{title, url}]}.

Dispatch: duckduckgo (free, no key) | tavily.
"""
import asyncio

from settings import Settings


async def web_search(s: Settings, query: str) -> dict:
    if s.search_provider == "tavily":
        return await _tavily(s, query)
    return await _duckduckgo(query)


# ---------- DuckDuckGo (free, no key) ----------
async def _duckduckgo(query: str) -> dict:
    def go():
        from ddgs import DDGS

        return list(DDGS().text(query, max_results=4))

    rows = await asyncio.to_thread(go)
    sources = [
        {"title": r.get("title", ""), "url": r.get("href") or r.get("url", "")}
        for r in rows
    ]
    answer = " ".join((r.get("body") or r.get("snippet") or "") for r in rows).strip()
    return {"answer": answer, "sources": sources}


# ---------- Tavily ----------
_tv_clients: dict = {}


def _tavily_client(key: str):
    if not key:
        raise RuntimeError("TAVILY_API_KEY 未设置（SEARCH_PROVIDER=tavily 时需要）")
    if key not in _tv_clients:
        from tavily import TavilyClient

        _tv_clients[key] = TavilyClient(api_key=key)
    return _tv_clients[key]


async def _tavily(s: Settings, query: str) -> dict:
    def go():
        return _tavily_client(s.tavily_api_key).search(
            query=query, search_depth="advanced", max_results=3, include_answer=True
        )

    res = await asyncio.to_thread(go)
    return {
        "answer": res.get("answer", "") or "",
        "sources": [
            {"title": r.get("title", ""), "url": r.get("url", "")}
            for r in res.get("results", [])
        ],
    }
