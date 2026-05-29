"""Article extraction: url -> {"title": str, "text": str}.

Bundled engine: trafilatura (open-source). To use a hosted extractor instead
(Tavily Extract, Mercury, Readability service, …), branch here.
"""
import asyncio

from settings import Settings


async def extract_article(s: Settings, url: str) -> dict:
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
