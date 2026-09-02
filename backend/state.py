import asyncio
import glob
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

JOB_TTL = 6 * 3600  # seconds a finished job (and its mp3) is kept around

# (step_id, human label). Drives both the SSE protocol and the UI checklist.
STEPS = [
    ("ingest", "解析来源 & 转写"),
    ("extract", "提取核心重点"),
    ("research", "网络深度检索"),
    ("script", "撰写播客脚本"),
    ("tts", "语音合成"),
]


@dataclass
class Job:
    id: str
    created: float = field(default_factory=time.time)
    queue: "asyncio.Queue" = field(default_factory=asyncio.Queue)
    status: str = "pending"  # pending | running | done | error
    result: Optional[dict] = None
    error: Optional[str] = None


JOBS: dict[str, Job] = {}


def new_job() -> Job:
    job = Job(id=uuid.uuid4().hex[:12])
    JOBS[job.id] = job
    return job


def sweep(audio_dir: str, ttl: float = JOB_TTL) -> int:
    """Forget finished jobs older than `ttl` and delete the mp3 each one produced.
    Without this both JOBS and static/audio/ grow for as long as the process lives.

    Only files belonging to a job this process created are touched, so anything
    already sitting in the directory (samples, files orphaned by an earlier restart)
    is left alone."""
    cutoff = time.time() - ttl
    stale = [jid for jid, job in JOBS.items()
             if job.created < cutoff and job.status in ("done", "error")]
    for jid in stale:
        JOBS.pop(jid, None)
        for path in glob.glob(os.path.join(audio_dir, f"{jid}.*")):
            try:
                os.remove(path)
            except OSError:
                pass
    return len(stale)
