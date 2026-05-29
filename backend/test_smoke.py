"""Fast suite: deterministic units + BYOK wiring + regression for fixed bugs
+ live free-engine checks (no LLM, no paid keys)."""
import asyncio
import inspect
import io
import sys
import wave

from pipeline.extract import extract_key_points
from pipeline.ingest import _AUDIO_EXT, _yt_id, ingest
from pipeline.llm import safe_json
from pipeline.research import deep_research
from pipeline.script import build_script
from providers.extract import extract_article
from providers.search import web_search
from providers.tts import (
    EDGE_VOICES,
    _concat_wav,
    _split,
    _wav_duration,
    synthesize,
)
from settings import resolve

PASS, FAIL = [], []


def check(name, cond):
    (PASS if cond else FAIL).append(name)
    print(("PASS " if cond else "FAIL "), name)


# --- settings / BYOK resolution ---
s = resolve({"llm_api_key": "k", "tts_provider": "gradium", "wpm": "200"})
check("settings override wins", s.llm_api_key == "k" and s.tts_provider == "gradium" and s.wpm == 200)
d = resolve({})
check("settings default free", d.tts_provider == "edge" and d.search_provider == "duckduckgo" and d.extract_provider == "trafilatura")

# --- BYOK contract: every stage takes Settings as first arg ---
for fn in [extract_key_points, deep_research, ingest, build_script, synthesize, web_search, extract_article]:
    check(f"threads Settings: {fn.__name__}", list(inspect.signature(fn).parameters)[0] == "s")

# --- regression: safe_json must never raise (the crash we fixed) ---
check("safe_json valid", safe_json('{"a":1}') == {"a": 1})
check("safe_json fenced", safe_json('```json\n{"a":1}\n```') == {"a": 1})
check("safe_json trailing comma", safe_json('{"a":1,}') == {"a": 1})
check("safe_json missing-comma -> {} (no raise)", safe_json('{"a":1 "b":2}') == {})
check("safe_json garbage -> {}", safe_json("not json") == {})
check("safe_json empty -> {}", safe_json("") == {})

# --- deterministic helpers ---
check("yt id youtu.be", _yt_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ")
check("yt id watch", _yt_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ")
check("yt id none", _yt_id("https://example.com/x") is None)
check("audio ext set", ".mp3" in _AUDIO_EXT)
check("edge zh voice", EDGE_VOICES["中文"].startswith("zh-"))
ch = _split("A" * 1700 + ". " + "B" * 1700 + ". " + "C" * 100)
check("split respects limit", all(len(c) <= 1800 for c in ch))


def _mkwav(sec, rate=8000):
    b = io.BytesIO()
    w = wave.open(b, "wb")
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(rate)
    w.writeframes(b"\x00\x00" * int(rate * sec))
    w.close()
    return b.getvalue()


check("wav concat duration", abs(_wav_duration(_concat_wav([_mkwav(1), _mkwav(2)])) - 3.0) < 0.05)


# --- live free engines (network, but no keys) ---
async def live():
    fs = resolve({})
    o = await synthesize(fs, "This is a short English test for podcast2go.", "English")
    check("edge-tts EN (mp3+duration)", o["ext"] == "mp3" and len(o["audio"]) > 1000 and o["duration"] > 0)
    o = await synthesize(fs, "这是一段中文测试。", "中文")
    check("edge-tts 中文 (mp3+duration)", len(o["audio"]) > 1000 and o["duration"] > 0)
    r = await web_search(fs, "retrieval augmented generation")
    check("duckduckgo search", len(r["sources"]) >= 1 and r["sources"][0]["url"].startswith("http"))
    a = await extract_article(fs, "https://en.wikipedia.org/wiki/Podcast")
    check("trafilatura extract", len(a["text"]) > 500 and bool(a["title"]))
    try:
        y = await ingest(fs, "https://www.youtube.com/watch?v=aircAruvnKk")
        check("youtube ingest (captions)", len(y["text"]) > 200)
    except Exception as e:
        print("SKIP  youtube ingest (network/blocked):", type(e).__name__, str(e)[:80])


asyncio.run(live())

print(f"\n=== {len(PASS)} passed, {len(FAIL)} failed ===")
if FAIL:
    print("FAILED:", FAIL)
    sys.exit(1)
