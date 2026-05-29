"""Gradium TTS: spoken script -> wav bytes. Chunks long text and concatenates."""
import io
import re
import wave

from gradium import GradiumClient

from config import GRADIUM_API_KEY, GRADIUM_BASE_URL, GRADIUM_VOICE_ID

CHUNK_CHARS = 1800


def _client() -> GradiumClient:
    kw = {}
    if GRADIUM_API_KEY:
        kw["api_key"] = GRADIUM_API_KEY
    if GRADIUM_BASE_URL:
        kw["base_url"] = GRADIUM_BASE_URL
    return GradiumClient(**kw)


def _split(text: str, limit: int = CHUNK_CHARS) -> list[str]:
    sents = re.split(r"(?<=[.!?])\s+", text.strip())
    chunks, cur = [], ""
    for s in sents:
        if cur and len(cur) + len(s) + 1 > limit:
            chunks.append(cur)
            cur = s
        else:
            cur = f"{cur} {s}".strip()
    if cur:
        chunks.append(cur)
    return chunks or [text]


def _concat_wav(parts: list[bytes]) -> bytes:
    out = io.BytesIO()
    writer = None
    for b in parts:
        r = wave.open(io.BytesIO(b), "rb")
        if writer is None:
            writer = wave.open(out, "wb")
            writer.setnchannels(r.getnchannels())
            writer.setsampwidth(r.getsampwidth())
            writer.setframerate(r.getframerate())
        writer.writeframes(r.readframes(r.getnframes()))
        r.close()
    if writer:
        writer.close()
    return out.getvalue()


async def synthesize(text: str, voice_id: str | None = None, fmt: str = "wav") -> bytes:
    client = _client()
    voice_id = voice_id or GRADIUM_VOICE_ID
    raws = []
    for part in _split(text):
        audio = await client.tts(
            setup={"voice_id": voice_id, "output_format": fmt}, text=part
        )
        raws.append(audio.raw_data)
    if len(raws) == 1:
        return raws[0]
    return _concat_wav(raws)


def wav_duration(b: bytes) -> float:
    r = wave.open(io.BytesIO(b), "rb")
    try:
        return r.getnframes() / float(r.getframerate())
    finally:
        r.close()
