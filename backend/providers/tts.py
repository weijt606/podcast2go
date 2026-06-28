"""TTS: spoken script -> audio bytes.

Two engines, picked by s.tts_engine:
  - "edge" (default): edge-tts, free, no key, voice auto-by-language or picked.
  - "api": any OpenAI-compatible /v1/audio/speech (OpenAI TTS, compatible hosts).

Two shapes:
  - synthesize(s, text, language, voice)         -> single-voice monologue
  - synthesize_dialogue(s, segments, language, host_voice, guest_voice)
        segments = [{"speaker": "host"|"guest", "text": str}, ...]

Both return {"audio": bytes, "ext": "mp3", "duration": seconds}.
"""
import io

from settings import Settings

# edge-tts voice picked by the requested output language (single-host default)
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

# [host, guest] fallbacks for dialogue when the request leaves voices blank
DIALOGUE_DEFAULTS = {
    "English": ["en-US-AvaNeural", "en-US-AndrewNeural"],
    "Chinese": ["zh-CN-XiaoxiaoNeural", "zh-CN-YunxiNeural"],
    "中文": ["zh-CN-XiaoxiaoNeural", "zh-CN-YunxiNeural"],
}


def _default_voice(language: str, idx: int) -> str:
    pair = DIALOGUE_DEFAULTS.get(language)
    if pair:
        return pair[idx]
    base = EDGE_VOICES.get(language, "en-US-AriaNeural")
    return base if idx == 0 else EDGE_VOICES.get(language and "English", "en-US-GuyNeural")


async def synthesize(s: Settings, text: str, language: str = "English", voice: str = "") -> dict:
    if s.tts_engine == "api":
        return await _synth_api(s, text)
    data = await _edge_bytes(s, text, voice, language)
    if not data:
        raise RuntimeError("TTS 合成结果为空")
    return {"audio": data, "ext": "mp3", "duration": _mp3_duration(data)}


async def synthesize_dialogue(s: Settings, segments: list[dict], language: str = "English",
                              host_voice: str = "", guest_voice: str = "") -> dict:
    # API engine has a single voice — read the joined text in one voice (no labels).
    if s.tts_engine == "api":
        return await _synth_api(s, "\n".join(seg["text"] for seg in segments))

    host_voice = host_voice or _default_voice(language, 0)
    guest_voice = guest_voice or _default_voice(language, 1)
    audio = bytearray()
    total = 0.0
    for seg in segments:
        v = host_voice if seg.get("speaker") == "host" else guest_voice
        part = await _edge_bytes(s, seg["text"], v, language)
        if part:
            audio.extend(part)
            total += _mp3_duration(part)
    data = bytes(audio)
    if not data:
        raise RuntimeError("对谈语音合成为空")
    return {"audio": data, "ext": "mp3", "duration": round(total, 1)}


async def _edge_bytes(s: Settings, text: str, voice: str, language: str) -> bytes:
    import edge_tts

    v = voice or s.edge_voice or EDGE_VOICES.get(language, "en-US-AriaNeural")
    comm = edge_tts.Communicate(text, v)
    audio = bytearray()
    async for ch in comm.stream():
        if ch["type"] == "audio":
            audio.extend(ch["data"])
    return bytes(audio)


async def _synth_api(s: Settings, text: str) -> dict:
    from openai import AsyncOpenAI

    if not s.tts_api_key:
        raise RuntimeError("TTS API key 未设置（在前端设置里填入，或配置 backend/.env）")
    client = AsyncOpenAI(base_url=s.tts_base_url or None, api_key=s.tts_api_key)
    model = s.tts_model or "tts-1"
    voice = s.tts_voice or "alloy"
    async with client.audio.speech.with_streaming_response.create(
        model=model, voice=voice, input=text, response_format="mp3"
    ) as resp:
        data = await resp.read()
    if not data:
        raise RuntimeError("TTS API 返回空音频")
    return {"audio": data, "ext": "mp3", "duration": _mp3_duration(data)}


def _mp3_duration(b: bytes) -> float:
    from mutagen.mp3 import MP3

    return round(MP3(io.BytesIO(b)).info.length, 1)
