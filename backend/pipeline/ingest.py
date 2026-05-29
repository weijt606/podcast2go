"""Turn a URL into clean text.

article -> providers.extract ; YouTube -> captions ; audio file -> providers.stt
"""
import asyncio
import json
import re
import urllib.parse
import urllib.request

from providers.extract import extract_article
from settings import Settings

_YT = re.compile(
    r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/|youtube\.com/shorts/)([\w-]{11})"
)
_AUDIO_EXT = (".mp3", ".m4a", ".wav", ".aac", ".ogg", ".flac", ".opus")


def _yt_id(url: str):
    m = _YT.search(url)
    return m.group(1) if m else None


async def ingest(s: Settings, url: str) -> dict:
    vid = _yt_id(url)
    if vid:
        return await asyncio.to_thread(_youtube, vid, url)
    if url.split("?")[0].lower().endswith(_AUDIO_EXT):
        return await _audio(s, url)
    res = await extract_article(s, url)
    return {"title": res["title"], "text": res["text"], "source_type": "article", "source_url": url}


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


async def _audio(s: Settings, url: str) -> dict:
    from providers.stt import transcribe

    text = await transcribe(s, url)
    return {
        "title": urllib.parse.unquote(url.split("?")[0].rstrip("/").split("/")[-1]) or "Audio",
        "text": text,
        "source_type": "audio",
        "source_url": url,
    }
