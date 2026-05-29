"""Article extraction: url -> {"title": str, "text": str}.

Dispatch: trafilatura (open-source) | tavily.
"""
import asyncio

from settings import Settings


async def extract_article(s: Settings, url: str) -> dict:
    if s.extract_provider == "tavily":
        return await _tavily(s, url)
    return await _trafilatura(url)


# ---------- trafilatura (open-source) ----------
async def _trafilatura(url: str) -> dict:
    def go():
        import trafilatura

        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            raise RuntimeError("无法下载页面（trafilatura）")
        text = trafilatura.extract(
            downloaded, include_comments=False, include_tables=False
        ) or ""
        meta = trafilatura.extract_metadata(downloaded)
        title = (meta.title if meta and meta.title else "") or url.rstrip("/").split("/")[-1] or "Article"
        return {"title": title, "text": text.strip()}

    res = await asyncio.to_thread(go)
    if not res["text"]:
        raise RuntimeError("文章正文为空")
    return res


# ---------- Tavily ----------
_tv_clients: dict = {}


def _tavily_client(key: str):
    if not key:
        raise RuntimeError("TAVILY_API_KEY 未设置（EXTRACT_PROVIDER=tavily 时需要）")
    if key not in _tv_clients:
        from tavily import TavilyClient

        _tv_clients[key] = TavilyClient(api_key=key)
    return _tv_clients[key]


async def _tavily(s: Settings, url: str) -> dict:
    def go():
        return _tavily_client(s.tavily_api_key).extract(urls=[url])

    res = await asyncio.to_thread(go)
    results = res.get("results", [])
    if not results:
        raise RuntimeError("无法提取文章正文（Tavily extract 返回空）")
    first = results[0]
    raw = (first.get("raw_content") or "").strip()
    if not raw:
        raise RuntimeError("文章正文为空")
    title = first.get("title") or url.rstrip("/").split("/")[-1] or "Article"
    return {"title": title, "text": raw}
