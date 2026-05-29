"""Web search: query -> {"answer": str, "sources": [{title, url}]}.

Bundled engine: DuckDuckGo (free, no key). To use a search API instead
(Tavily, Brave, Serper, …), branch on the query here and return the same shape.
"""
import asyncio

from settings import Settings


async def web_search(s: Settings, query: str) -> dict:
    def go():
        from ddgs import DDGS

        return list(DDGS().text(query, max_results=4))

    rows = await asyncio.to_thread(go)
    sources = [
        {"title": r.get("title", ""), "url": r.get("href") or r.get("url", "")}
        for r in rows
    ]
    # no synthesized answer from search; hand the snippets to the script LLM as-is
    answer = " ".join((r.get("body") or r.get("snippet") or "") for r in rows).strip()
    return {"answer": answer, "sources": sources}
