"""Fast suite: deterministic units + BYOK wiring + regression for fixed bugs
+ live free-engine checks (no LLM, no paid keys)."""
import asyncio
import inspect
import sys

from pipeline.extract import extract_key_points
from pipeline.ingest import _AUDIO_EXT, _yt_id, ingest
from pipeline.llm import safe_json
from pipeline.research import deep_research
from pipeline.script import build_script
from providers.extract import extract_article
from providers.search import web_search
from providers.tts import EDGE_VOICES, synthesize
from settings import resolve

PASS, FAIL = [], []


def check(name, cond):
    (PASS if cond else FAIL).append(name)
    print(("PASS " if cond else "FAIL "), name)


# --- settings / BYOK resolution ---
s = resolve({"llm_api_key": "k", "llm_model": "m", "wpm": "200"})
check("settings override wins", s.llm_api_key == "k" and s.llm_model == "m" and s.wpm == 200)
d = resolve({})
check("settings default from env", bool(d.llm_base_url) and d.wpm == 150)

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
