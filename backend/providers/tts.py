"""TTS: spoken script -> audio bytes, via edge-tts (free, no key).

Returns {"audio": bytes, "ext": "mp3", "duration": seconds}.
To add a paid engine (OpenAI TTS, ElevenLabs, Azure, Piper, …), branch on
s.* and return the same shape.
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


def _mp3_duration(b: bytes) -> float:
    from mutagen.mp3 import MP3

    return round(MP3(io.BytesIO(b)).info.length, 1)
