import asyncio
import json
import os

from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from pipeline.orchestrator import run_pipeline
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


@app.post("/api/generate")
async def generate(req: GenReq):
    job = new_job()
    asyncio.create_task(run_pipeline(job, req.model_dump()))
    return {"job_id": job.id, "steps": STEPS}


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
