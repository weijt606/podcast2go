"""Deep-search the most important key points to enrich them (concurrent)."""
import asyncio

from providers.search import web_search
from settings import Settings


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


async def _search_one(s: Settings, point: dict) -> dict:
    try:
        res = await web_search(s, point["point"])
    except Exception as e:
        return {"point": point["point"], "answer": f"(搜索失败: {e})", "sources": []}
    return {"point": point["point"], "answer": res.get("answer", ""), "sources": res.get("sources", [])}


async def deep_research(s: Settings, key_points: list[dict], deep_topics: str = "", top_n: int = 3) -> list[dict]:
    selected = _select(key_points, deep_topics, top_n)
    return list(await asyncio.gather(*[_search_one(s, p) for p in selected]))
