"""TTS: spoken script -> audio bytes. Dispatch: edge (free) | gradium.

Returns {"audio": bytes, "ext": "mp3"|"wav", "duration": seconds}.
"""
import io
import re
import wave

from settings import Settings

CHUNK_CHARS = 1800

# edge-tts voice picked by the requested output language
EDGE_VOICES = {
    "English": "en-US-AriaNeural",
    "Chinese": "zh-CN-XiaoxiaoNeural",
    "中文": "zh-CN-XiaoxiaoNeural",
    "French": "fr-FR-DeniseNeural",
    "German": "de-DE-KatjaNeural",
    "Spanish": "es-ES-ElviraNeural",
    "Portuguese": "pt-BR-FranciscaNeural",
    "Japanese": "ja-JP-NanamiNeural",
}


async def synthesize(s: Settings, text: str, language: str = "English") -> dict:
    if s.tts_provider == "gradium":
        return await _gradium(s, text)
    return await _edge(s, text, language)


# ---------- edge-tts (free, no API key, multi-language) ----------
async def _edge(s: Settings, text: str, language: str) -> dict:
    import edge_tts

    voice = s.edge_voice or EDGE_VOICES.get(language, "en-US-AriaNeural")
    comm = edge_tts.Communicate(text, voice)
    audio = bytearray()
    async for ch in comm.stream():
        if ch["type"] == "audio":
            audio.extend(ch["data"])
    data = bytes(audio)
    return {"audio": data, "ext": "mp3", "duration": _mp3_duration(data)}


def _mp3_duration(b: bytes) -> float:
    from mutagen.mp3 import MP3

    return round(MP3(io.BytesIO(b)).info.length, 1)


# ---------- Gradium ----------
async def _gradium(s: Settings, text: str) -> dict:
    from gradium import GradiumClient

    kw = {}
    if s.gradium_api_key:
        kw["api_key"] = s.gradium_api_key
    if s.gradium_base_url:
        kw["base_url"] = s.gradium_base_url
    client = GradiumClient(**kw)

    raws = []
    for part in _split(text):
        audio = await client.tts(
            setup={"voice_id": s.gradium_voice_id, "output_format": "wav"}, text=part
        )
        raws.append(audio.raw_data)
    data = raws[0] if len(raws) == 1 else _concat_wav(raws)
    return {"audio": data, "ext": "wav", "duration": _wav_duration(data)}


def _split(text: str, limit: int = CHUNK_CHARS) -> list[str]:
    sents = re.split(r"(?<=[.!?])\s+", text.strip())
    chunks, cur = [], ""
    for sent in sents:
        if cur and len(cur) + len(sent) + 1 > limit:
            chunks.append(cur)
            cur = sent
        else:
            cur = f"{cur} {sent}".strip()
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


def _wav_duration(b: bytes) -> float:
    r = wave.open(io.BytesIO(b), "rb")
    try:
        return round(r.getnframes() / float(r.getframerate()), 1)
    finally:
        r.close()
