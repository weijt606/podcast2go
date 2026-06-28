"""TTS: spoken script -> audio bytes.

Two engines, picked by s.tts_engine:
  - "edge" (default): edge-tts, free, no key, voice auto-by-language.
  - "api": any OpenAI-compatible /v1/audio/speech (OpenAI TTS, compatible hosts).

Returns {"audio": bytes, "ext": "mp3", "duration": seconds}.
To add another engine (Piper, CosyVoice, VoxCPM, …), add a branch below and
return the same shape.
"""
import io

from settings import Settings

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
    if s.tts_engine == "api":
        return await _synth_api(s, text)
    return await _synth_edge(s, text, language)


async def _synth_edge(s: Settings, text: str, language: str) -> dict:
    import edge_tts

    voice = s.edge_voice or EDGE_VOICES.get(language, "en-US-AriaNeural")
    comm = edge_tts.Communicate(text, voice)
    audio = bytearray()
    async for ch in comm.stream():
        if ch["type"] == "audio":
            audio.extend(ch["data"])
    data = bytes(audio)
    if not data:
        raise RuntimeError("TTS 合成结果为空")
    return {"audio": data, "ext": "mp3", "duration": _mp3_duration(data)}


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
