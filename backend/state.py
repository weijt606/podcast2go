import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Optional

# (step_id, human label). Drives both the SSE protocol and the UI checklist.
STEPS = [
    ("ingest", "解析来源 & 转写"),
    ("extract", "提取核心重点"),
    ("research", "Tavily 深度搜索"),
    ("script", "撰写播客脚本"),
    ("tts", "Gradium 语音合成"),
]


@dataclass
class Job:
    id: str
    queue: "asyncio.Queue" = field(default_factory=asyncio.Queue)
    status: str = "pending"  # pending | running | done | error
    result: Optional[dict] = None
    error: Optional[str] = None


JOBS: dict[str, Job] = {}


def new_job() -> Job:
    job = Job(id=uuid.uuid4().hex[:12])
    JOBS[job.id] = job
    return job
