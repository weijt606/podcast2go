"""Turn a URL into clean text. Article -> Tavily Extract; YouTube -> captions."""
import asyncio
import json
import re
import urllib.parse
import urllib.request

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


_YT = re.compile(r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/|youtube\.com/shorts/)([\w-]{11})")


def _yt_id(url: str):
    m = _YT.search(url)
    return m.group(1) if m else None


async def ingest(url: str) -> dict:
    vid = _yt_id(url)
    if vid:
        return await asyncio.to_thread(_youtube, vid, url)
    return await asyncio.to_thread(_article, url)


def _youtube(vid: str, url: str) -> dict:
    from youtube_transcript_api import YouTubeTranscriptApi

    segs = YouTubeTranscriptApi.get_transcript(
        vid, languages=["en", "en-US", "zh-Hans", "zh", "zh-Hant"]
    )
    text = " ".join(s["text"] for s in segs).strip()
    if not text:
        raise RuntimeError("该视频没有可用字幕")
    return {
        "title": _yt_title(url) or "YouTube Video",
        "text": text,
        "source_type": "youtube",
        "source_url": url,
    }


def _yt_title(url: str):
    try:
        q = urllib.parse.urlencode({"url": url, "format": "json"})
        with urllib.request.urlopen(f"https://www.youtube.com/oembed?{q}", timeout=8) as r:
            return json.load(r).get("title")
    except Exception:
        return None


def _article(url: str) -> dict:
    res = _tavily().extract(urls=[url])
    results = res.get("results", [])
    if not results:
        raise RuntimeError("无法提取文章正文（Tavily extract 返回空，检查 URL 或 key）")
    first = results[0]
    raw = (first.get("raw_content") or "").strip()
    if not raw:
        raise RuntimeError("文章正文为空")
    title = first.get("title") or url.rstrip("/").split("/")[-1] or "Article"
    return {"title": title, "text": raw, "source_type": "article", "source_url": url}
