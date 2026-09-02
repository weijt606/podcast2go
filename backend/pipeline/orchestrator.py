"""Runs the 5-stage pipeline for one job, emitting SSE progress as it goes."""
import asyncio
import os
import traceback

from state import Job

from providers.tts import synthesize, synthesize_dialogue
from settings import resolve

from .extract import extract_key_points
from .ingest import ingest
from .research import deep_research
from .script import build_script, count_units, length_unit

AUDIO_DIR = "static/audio"


async def _emit(job: Job, step: str, status: str, dkey: str = "", **dargs):
    """Progress events carry a key + args, not a sentence: the UI is bilingual and
    renders them in whichever language the user has selected."""
    await job.queue.put({"step": step, "status": status, "dkey": dkey, "dargs": dargs})


def _set_chapter_starts(chapters: list[dict], section_durations: list[float], total: float) -> bool:
    """Give each chapter its start time from the durations the TTS stage measured.

    Models are only loosely reliable about how many section markers they emit. Extra
    sections are harmless: the first n-1 boundaries are still real, so fold the tail
    into the last chapter. Too few sections gives us nothing to align, so fall back to
    an even split and report it, rather than hand the player wrong timestamps silently.
    """
    n = len(chapters)
    if not n or len(section_durations) < n:
        for i, ch in enumerate(chapters):
            ch["start"] = round(i / max(n, 1) * total, 1)
        return False

    spans = list(section_durations[:n - 1]) + [sum(section_durations[n - 1:])]
    t = 0.0
    for ch, d in zip(chapters, spans):
        ch["start"] = round(t, 1)
        t += d
    return True


async def run_pipeline(job: Job, req: dict):
    try:
        job.status = "running"
        s = resolve(req)
        loop = asyncio.get_running_loop()

        # STT runs in a worker thread; hop back to the loop to publish its progress
        def stt_progress(key: str, **args):
            loop.call_soon_threadsafe(
                job.queue.put_nowait,
                {"step": "ingest", "status": "running", "dkey": key, "dargs": args},
            )

        await _emit(job, "ingest", "running", "fetching")
        src = await ingest(s, req["url"], stt_progress)
        await _emit(job, "ingest", "done", "source",
                    title=src["title"], chars=len(src["text"]))

        language = req.get("language", "English")
        await _emit(job, "extract", "running", "extracting")
        ext = await extract_key_points(s, src["title"], src["text"],
                                       req.get("focus", ""), language)
        kps = ext["key_points"]
        await _emit(job, "extract", "done", "points", n=len(kps))

        await _emit(job, "research", "running", "searching")
        research = await deep_research(s, kps, req.get("deep_topics", ""))
        await _emit(job, "research", "done", "enriched", n=len(research))

        mode = req.get("mode", "single")
        await _emit(job, "script", "running", "writing")
        sc = await build_script(
            s, src["title"], ext.get("summary", ""), kps, research,
            req["minutes"], req.get("prefs", ""), language, mode,
        )
        script_text = sc["script"]
        await _emit(job, "script", "done", "words",
                    n=count_units(script_text), unit=length_unit(language))

        segments = sc.get("segments")
        await _emit(job, "tts", "running", "tts_dialogue" if segments else "tts_single")
        if segments:
            tts = await synthesize_dialogue(
                s, segments, language, req.get("voice", ""), req.get("voice2", ""),
            )
        else:
            tts = await synthesize(
                s, script_text, language, req.get("voice", ""), sc.get("sections"),
            )
        os.makedirs(AUDIO_DIR, exist_ok=True)
        audio_path = f"{AUDIO_DIR}/{job.id}.{tts['ext']}"
        with open(audio_path, "wb") as f:
            f.write(tts["audio"])
        dur = tts["duration"]
        await _emit(job, "tts", "done", "secs", n=round(dur))

        chapters = sc.get("chapters", [])
        measured = _set_chapter_starts(chapters, tts.get("sections") or [], dur)

        job.result = {
            "title": src["title"],
            "source_url": req["url"],
            "audio_url": f"/audio/{job.id}.{tts['ext']}",
            "duration": round(dur, 1),
            "target_minutes": req["minutes"],
            "key_points": kps,
            "research": research,
            "chapters": chapters,
            "chapters_measured": measured,
            "script": script_text,
        }
        job.status = "done"
        await _emit(job, "__done__", "done", "finished")
    except Exception as e:
        job.status = "error"
        job.error = str(e)
        traceback.print_exc()
        await job.queue.put({"step": "__done__", "status": "error",
                             "detail": f"{type(e).__name__}: {e}"})
