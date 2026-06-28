"""Turn a URL into clean text.

article -> providers.extract ; YouTube -> captions ;
Apple Podcasts / RSS feed / direct audio file -> providers.stt
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
_FEED_EXT = (".xml", ".rss")
_UA = "Mozilla/5.0 (podcast2go)"


def _yt_id(url: str):
    m = _YT.search(url)
    return m.group(1) if m else None


async def ingest(s: Settings, url: str) -> dict:
    vid = _yt_id(url)
    if vid:
        return await asyncio.to_thread(_youtube, vid, url)

    host = urllib.parse.urlparse(url).netloc.lower()
    if "podcasts.apple.com" in host or "podcast.apple.com" in host:
        audio_url, title = await asyncio.to_thread(_apple_audio, url)
        return await _audio(s, audio_url, title=title, source_url=url, source_type="podcast")

    if url.split("?")[0].lower().endswith(_AUDIO_EXT):
        return await _audio(s, url)

    if url.split("?")[0].lower().endswith(_FEED_EXT):
        audio_url, title = await asyncio.to_thread(_rss_resolve, url)
        return await _audio(s, audio_url, title=title, source_url=url, source_type="podcast")

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


# ---- podcast resolution (URL -> direct audio enclosure) ----

def _get(url: str, timeout: int = 15) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _itunes_lookup(**params) -> dict:
    q = urllib.parse.urlencode(params)
    raw = _get(f"https://itunes.apple.com/lookup?{q}", timeout=12)
    return json.loads(raw.decode("utf-8", "ignore"))


def _apple_audio(url: str) -> tuple[str, str | None]:
    """Resolve an Apple Podcasts link to a direct episode audio URL via iTunes."""
    cm = re.search(r"/id(\d+)", url)
    em = re.search(r"[?&]i=(\d+)", url)
    coll = cm.group(1) if cm else None
    epi = em.group(1) if em else None

    # 1. direct episode-id lookup
    if epi:
        for r in _itunes_lookup(id=epi, entity="podcastEpisode").get("results", []):
            if r.get("episodeUrl"):
                return r["episodeUrl"], r.get("trackName")

    # 2. collection's episodes -> match the requested one, else the latest
    if coll:
        results = _itunes_lookup(id=coll, entity="podcastEpisode", limit=200).get("results", [])
        eps = [r for r in results if r.get("episodeUrl")]
        if epi:
            for r in eps:
                if str(r.get("trackId")) == epi:
                    return r["episodeUrl"], r.get("trackName")
        if eps:
            return eps[0]["episodeUrl"], eps[0].get("trackName")
        feed = next((r.get("feedUrl") for r in results if r.get("feedUrl")), None)
        if feed:
            return _rss_resolve(feed)

    raise RuntimeError("无法从该 Apple Podcasts 链接解析出音频（可能是地区限制或单集已下架）")


def _rss_resolve(url: str) -> tuple[str, str | None]:
    """Take a podcast RSS feed URL and return its latest episode's audio + title."""
    import xml.etree.ElementTree as ET

    root = ET.fromstring(_get(url))
    channel = root.find("channel") if root.find("channel") is not None else root
    item = channel.find("item")
    if item is None:
        raise RuntimeError("RSS 中没有可用单集")
    enc = item.find("enclosure")
    audio = enc.get("url") if enc is not None else None
    if not audio:
        raise RuntimeError("RSS 单集没有音频附件")
    title = (item.findtext("title") or "").strip() or None
    return audio, title


async def _audio(s: Settings, url: str, title: str | None = None,
                 source_url: str | None = None, source_type: str = "audio") -> dict:
    from providers.stt import transcribe

    text = await transcribe(s, url)
    fallback = urllib.parse.unquote(url.split("?")[0].rstrip("/").split("/")[-1]) or "Audio"
    return {
        "title": title or fallback,
        "text": text,
        "source_type": source_type,
        "source_url": source_url or url,
    }
