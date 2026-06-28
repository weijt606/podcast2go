import asyncio
import base64
import json
import os

from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import settings
from pipeline import llm
from pipeline.orchestrator import run_pipeline
from providers.tts import synthesize
from state import JOBS, STEPS, new_job

app = FastAPI(title="podcast2go")

os.makedirs("static/audio", exist_ok=True)


class GenReq(BaseModel):
    url: str
    minutes: int = 5
    focus: str = ""
    deep_topics: str = ""
    prefs: str = ""
    language: str = "English"
    mode: str = "single"          # "single" monologue | "dialogue" two-host
    voice: str = ""               # edge voice for host/narrator
    voice2: str = ""              # edge voice for the guest (dialogue mode)
    # BYOK: optional per-request overrides; blank -> fall back to backend/.env
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_model: str = ""
    tts_engine: str = ""
    tts_base_url: str = ""
    tts_api_key: str = ""
    tts_model: str = ""
    tts_voice: str = ""


@app.post("/api/generate")
async def generate(req: GenReq):
    job = new_job()
    asyncio.create_task(run_pipeline(job, req.model_dump()))
    return {"job_id": job.id, "steps": STEPS}


class LLMTestReq(BaseModel):
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_model: str = ""


@app.post("/api/test_llm")
async def test_llm(req: LLMTestReq):
    """Probe the configured LLM endpoint with a tiny completion."""
    s = settings.resolve(req.model_dump())
    try:
        reply = await llm.chat(s, "You are a connectivity probe.", "Reply with the single word: ok",
                               json_mode=False, temperature=0)
        return {"ok": True, "detail": (reply or "").strip()[:80] or "connected"}
    except Exception as e:
        return {"ok": False, "detail": str(e)[:300]}


class TTSTestReq(BaseModel):
    language: str = "English"
    tts_engine: str = ""
    tts_base_url: str = ""
    tts_api_key: str = ""
    tts_model: str = ""
    tts_voice: str = ""
    voice: str = ""  # edge voice to preview (overrides the auto-by-language pick)


@app.post("/api/test_tts")
async def test_tts(req: TTSTestReq):
    """Synthesize a short sample so the user can confirm the engine / preview a voice."""
    s = settings.resolve(req.model_dump())
    sample = "你好，这是 podcast2go 的语音测试。" if (req.language or "").startswith(("中", "Chinese")) \
        else "Hello, this is a podcast2go voice test."
    try:
        out = await synthesize(s, sample, req.language or "English", req.voice)
        b64 = base64.b64encode(out["audio"]).decode()
        return {"ok": True, "detail": f"{out['duration']:.1f}s · {out['ext']}",
                "sample": f"data:audio/{out['ext']};base64,{b64}"}
    except Exception as e:
        return {"ok": False, "detail": str(e)[:300]}


@app.get("/api/events/{job_id}")
async def events(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        return JSONResponse({"error": "job not found"}, status_code=404)

    async def gen():
        while True:
            ev = await job.queue.get()
            yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
            if ev.get("step") == "__done__":
                break

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/api/result/{job_id}")
async def result(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        return JSONResponse({"error": "job not found"}, status_code=404)
    if job.status == "error":
        return JSONResponse({"error": job.error}, status_code=500)
    if not job.result:
        return JSONResponse({"error": "not ready"}, status_code=409)
    return job.result


# audio files + single-page frontend (declared after API routes so they take precedence)
app.mount("/audio", StaticFiles(directory="static/audio"), name="audio")
app.mount("/", StaticFiles(directory="static", html=True), name="ui")
