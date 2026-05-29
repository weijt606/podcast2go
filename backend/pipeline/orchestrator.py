"""Runs the 5-stage pipeline for one job, emitting SSE progress as it goes."""
import os
import traceback

from state import Job

from providers.tts import synthesize
from settings import resolve

from .extract import extract_key_points
from .ingest import ingest
from .research import deep_research
from .script import build_script

AUDIO_DIR = "static/audio"


async def _emit(job: Job, step: str, status: str, detail: str = "", **extra):
    await job.queue.put({"step": step, "status": status, "detail": detail, **extra})


async def run_pipeline(job: Job, req: dict):
    try:
        job.status = "running"
        s = resolve(req)

        await _emit(job, "ingest", "running", "获取内容中…")
        src = await ingest(s, req["url"])
        await _emit(job, "ingest", "done", f"《{src['title']}》· {len(src['text'])} 字符")

        await _emit(job, "extract", "running", "提取重点中…")
        ext = await extract_key_points(s, src["title"], src["text"], req.get("focus", ""))
        kps = ext["key_points"]
        await _emit(job, "extract", "done", f"{len(kps)} 个核心点")

        await _emit(job, "research", "running", "深度搜索中…")
        research = await deep_research(s, kps, req.get("deep_topics", ""))
        await _emit(job, "research", "done", f"{len(research)} 个主题已补充")

        await _emit(job, "script", "running", "撰写脚本中…")
        sc = await build_script(
            s, src["title"], ext.get("summary", ""), kps, research,
            req["minutes"], req.get("prefs", ""), req.get("language", "English"),
        )
        script_text = sc["script"]
        await _emit(job, "script", "done", f"~{len(script_text.split())} 词")

        await _emit(job, "tts", "running", "语音合成中…")
        tts = await synthesize(s, script_text, req.get("language", "English"))
        os.makedirs(AUDIO_DIR, exist_ok=True)
        audio_path = f"{AUDIO_DIR}/{job.id}.{tts['ext']}"
        with open(audio_path, "wb") as f:
            f.write(tts["audio"])
        dur = tts["duration"]
        await _emit(job, "tts", "done", f"{dur:.0f} 秒")

        # approximate chapter start times by even split across the audio
        chapters = sc.get("chapters", [])
        n = max(len(chapters), 1)
        for i, ch in enumerate(chapters):
            ch["start"] = round(i / n * dur, 1)

        job.result = {
            "title": src["title"],
            "source_url": req["url"],
            "audio_url": f"/audio/{job.id}.{tts['ext']}",
            "duration": round(dur, 1),
            "target_minutes": req["minutes"],
            "key_points": kps,
            "research": research,
            "chapters": chapters,
            "script": script_text,
        }
        job.status = "done"
        await _emit(job, "__done__", "done", "完成")
    except Exception as e:
        job.status = "error"
        job.error = str(e)
        traceback.print_exc()
        await _emit(job, "__done__", "error", f"{type(e).__name__}: {e}")
