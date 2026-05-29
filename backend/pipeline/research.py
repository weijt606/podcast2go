"""Tavily deep search to enrich the most important key points (concurrent)."""
import asyncio

from tavily import TavilyClient

from config import TAVILY_API_KEY

_tv: TavilyClient | None = None


def _tavily() -> TavilyClient:
    global _tv
    if _tv is None:
        if not TAVILY_API_KEY:
            raise RuntimeError("TAVILY_API_KEY 未设置（请在 backend/.env 配置）")
        _tv = TavilyClient(api_key=TAVILY_API_KEY)
    return _tv


def _select(key_points: list[dict], deep_topics: str, top_n: int) -> list[dict]:
    topics = [t.strip().lower() for t in deep_topics.replace("，", ",").split(",") if t.strip()]
    if topics:
        matched = [
            p for p in key_points
            if any(t in (p.get("point", "") + p.get("detail", "")).lower() for t in topics)
        ]
        if matched:
            return matched[:top_n]
    return sorted(key_points, key=lambda p: -p.get("importance", 3))[:top_n]


async def _search_one(point: dict) -> dict:
    def go():
        return _tavily().search(
            query=point["point"], search_depth="advanced", max_results=3, include_answer=True
        )

    try:
        res = await asyncio.to_thread(go)
    except Exception as e:
        return {"point": point["point"], "answer": f"(搜索失败: {e})", "sources": []}
    return {
        "point": point["point"],
        "answer": res.get("answer", "") or "",
        "sources": [
            {"title": r.get("title", ""), "url": r.get("url", "")}
            for r in res.get("results", [])
        ],
    }


async def deep_research(key_points: list[dict], deep_topics: str = "", top_n: int = 3) -> list[dict]:
    selected = _select(key_points, deep_topics, top_n)
    return list(await asyncio.gather(*[_search_one(p) for p in selected]))
