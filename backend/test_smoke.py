"""Fast suite: deterministic units + BYOK wiring + regression for fixed bugs
+ live free-engine checks (no LLM, no paid keys)."""
import asyncio
import inspect
import sys

import os
import tempfile
import time

import pipeline.extract as extract_mod
from pipeline.extract import extract_key_points
from pipeline.ingest import _AUDIO_EXT, _yt_id, ingest
from pipeline.llm import safe_json
from pipeline.orchestrator import _set_chapter_starts
from pipeline.research import deep_research
from pipeline.script import (CJK_CHARS_PER_MIN, SECTION, _budget, _parse_dialogue,
                             _split_sections, build_script, count_units, length_unit)
from providers.extract import extract_article
from providers.search import web_search
from providers.tts import DIALOGUE_DEFAULTS, EDGE_VOICES, _default_voice, synthesize
from settings import resolve
from state import JOBS, Job, sweep

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

# --- regression: a dialogue guest must answer in the host's language ---
# `EDGE_VOICES.get(language and "English", ...)` always evaluated to "English", so a
# Japanese host got an American English guest. Locale prefixes must match.
for _lang in EDGE_VOICES:
    _host, _guest = _default_voice(_lang, 0), _default_voice(_lang, 1)
    check(f"dialogue voices share locale: {_lang}",
          _host.split("-")[0] == _guest.split("-")[0] and _host != _guest)
check("every voice language has a dialogue pair",
      set(EDGE_VOICES) <= set(DIALOGUE_DEFAULTS))

# --- section markers: what makes chapter offsets real instead of guessed ---
check("split sections", _split_sections(f"one\n{SECTION}\ntwo\n{SECTION}\nthree")
      == ["one", "two", "three"])
check("split without markers is one section", _split_sections("just one") == ["just one"])
check("marker never leaks into spoken text",
      all(SECTION not in s for s in _split_sections(f"a\n{SECTION}\nb")))
_segs = _parse_dialogue(f"HOST: hi\nGUEST: yo\n{SECTION}\nHOST: next")
check("dialogue segments carry section index",
      [g["section"] for g in _segs] == [0, 0, 1])

# --- length budget must be in the unit the output language is actually spoken in ---
# `len(text.split())` reports 6 for a 900-char Chinese script, and a 450-"word" budget
# for 3 min of Chinese is ~115s of audio, not 180s. Measured rate: 233 chars/min.
check("count_units counts CJK by character", count_units("播客很有意思") == 6)
check("count_units counts latin by word", count_units("a short english line") == 4)
check("count_units handles mixed text", count_units("播客 podcast 很好") == 5)
check("english budget stays words-per-minute", _budget(3, 150, "English") == (450, "words"))
check("chinese budget switches to chars-per-minute",
      _budget(3, 150, "中文") == (3 * CJK_CHARS_PER_MIN, "characters"))
check("japanese budgets like chinese", _budget(3, 150, "Japanese")[1] == "characters")
check("length_unit matches the budget unit",
      length_unit("中文") == "characters" and length_unit("English") == "words")

# --- chapter offsets: measured when we can, and honest when we can't ---
_ch = [{"title": "a"}, {"title": "b"}, {"title": "c"}]
check("measured offsets accumulate real durations",
      _set_chapter_starts(_ch, [10.0, 20.0, 5.0], 35.0) is True
      and [c["start"] for c in _ch] == [0.0, 10.0, 30.0])
_ch = [{"title": "a"}, {"title": "b"}, {"title": "c"}]
check("extra sections keep the real boundaries, tail folds into the last chapter",
      _set_chapter_starts(_ch, [10.0, 20.0, 5.0, 7.0], 42.0) is True
      and [c["start"] for c in _ch] == [0.0, 10.0, 30.0])
_ch = [{"title": "a"}, {"title": "b"}]
check("too few sections falls back to an even split and reports it",
      _set_chapter_starts(_ch, [10.0], 40.0) is False
      and [c["start"] for c in _ch] == [0.0, 20.0])
_ch = []
check("no chapters is not a crash", _set_chapter_starts(_ch, [], 10.0) is False)

# --- sweep must never touch files it did not create (user samples live there too) ---
_tmp = tempfile.mkdtemp()
_stranger = os.path.join(_tmp, "sample.mp3")
open(_stranger, "wb").write(b"x")
JOBS.clear()
_old = Job(id="old1", created=time.time() - 99999); _old.status = "done"
_fresh = Job(id="new1"); _fresh.status = "done"
JOBS["old1"], JOBS["new1"] = _old, _fresh
open(os.path.join(_tmp, "old1.mp3"), "wb").write(b"x")
open(os.path.join(_tmp, "new1.mp3"), "wb").write(b"x")
_n = sweep(_tmp, ttl=3600)
check("sweep drops the expired job only", _n == 1 and "old1" not in JOBS and "new1" in JOBS)
check("sweep deletes the expired job's audio", not os.path.exists(os.path.join(_tmp, "old1.mp3")))
check("sweep keeps the live job's audio", os.path.exists(os.path.join(_tmp, "new1.mp3")))
check("sweep leaves unknown files alone", os.path.exists(_stranger))
JOBS.clear()


# --- concurrent map must not scramble the source order of the bullets ---
_REDUCE_SAW = []


async def _fake_chat(s, system, user, **kw):
    import asyncio as _a
    if "(chunk " not in user:         # the reduce call: it receives the joined bullets
        _REDUCE_SAW.append(user)
        return '{"summary":"s","key_points":[{"point":"p","detail":"","importance":3}]}'
    n = int(user.split("(chunk ")[1].split("/")[0])
    await _a.sleep(0.05 / n)          # later chunks finish first if order isn't enforced
    return '{"points": ["chunk%02d"]}' % n


async def order_test():
    """Chunks now run concurrently, so they finish out of order. The bullets handed to
    the reduce step must still follow the source, or the ranking sees a shuffled
    transcript."""
    real, extract_mod.chat = extract_mod.chat, _fake_chat
    try:
        # 3 full chunks; the fake makes the LAST one return first
        await extract_key_points(resolve({"llm_api_key": "x"}), "t",
                                 "a" * (extract_mod.CHUNK * 3))
        seen = [ln for ln in _REDUCE_SAW[0].splitlines() if "chunk" in ln]
        check("parallel map preserves chunk order",
              seen == ["- chunk01", "- chunk02", "- chunk03"])
    finally:
        extract_mod.chat = real


asyncio.run(order_test())


# --- live free engines (network, but no keys) ---
async def live():
    fs = resolve({})
    o = await synthesize(fs, "This is a short English test for podcast2go.", "English")
    check("edge-tts EN (mp3+duration)", o["ext"] == "mp3" and len(o["audio"]) > 1000 and o["duration"] > 0)
    o = await synthesize(fs, "这是一段中文测试。", "中文")
    check("edge-tts 中文 (mp3+duration)", len(o["audio"]) > 1000 and o["duration"] > 0)

    # Measured chapter offsets only hold because edge-tts emits headerless CBR frames:
    # the concatenated file must measure as the sum of its parts, or every chapter
    # jump after the first lands in the wrong place.
    parts = ["First part of the test.", "Second part of the test.", "And a third part."]
    o = await synthesize(fs, " ".join(parts), "English", "", parts)
    check("per-section synthesis reports one duration per section",
          len(o["sections"]) == len(parts) and all(d > 0 for d in o["sections"]))
    check("concatenated mp3 measures as the sum of its sections",
          abs(o["duration"] - sum(o["sections"])) < 0.15)
    r = await web_search(fs, "retrieval augmented generation")
    check("duckduckgo search", len(r["sources"]) >= 1 and r["sources"][0]["url"].startswith("http"))
    a = await extract_article(fs, "https://en.wikipedia.org/wiki/Podcast")
    check("trafilatura extract", len(a["text"]) > 500 and bool(a["title"]))
    try:
        y = await ingest(fs, "https://www.youtube.com/watch?v=aircAruvnKk")
        check("youtube ingest (captions)", len(y["text"]) > 200)
    except Exception as e:
        print("SKIP  youtube ingest (network/blocked):", type(e).__name__, str(e)[:80])


# CI has no reliable route to DuckDuckGo, Wikipedia or Microsoft's TTS service, and a
# flaky required check blocks every merge. The deterministic half is the gate; the live
# half stays available locally, where it is the part that actually catches regressions
# in the engines themselves.
if os.getenv("P2G_SKIP_LIVE") == "1":
    print("SKIP  live engine checks (P2G_SKIP_LIVE=1)")
else:
    asyncio.run(live())

print(f"\n=== {len(PASS)} passed, {len(FAIL)} failed ===")
if FAIL:
    print("FAILED:", FAIL)
    sys.exit(1)
