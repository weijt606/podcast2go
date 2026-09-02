"""TTS: spoken script -> audio bytes.

Two engines, picked by s.tts_engine:
  - "edge" (default): edge-tts, free, no key, voice auto-by-language or picked.
  - "api": any OpenAI-compatible /v1/audio/speech (OpenAI TTS, compatible hosts).

Two shapes:
  - synthesize(s, text, language, voice)         -> single-voice monologue
  - synthesize_dialogue(s, segments, language, host_voice, guest_voice)
        segments = [{"speaker": "host"|"guest", "text": str}, ...]

Both return {"audio": bytes, "ext": "mp3", "duration": seconds,
             "sections": [per-section seconds]}.

"sections" is empty for the "api" engine, which synthesizes in one call and so
cannot time the parts.
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

# [host, guest] fallbacks for dialogue when the request leaves voices blank.
# Every language in EDGE_VOICES needs a pair, otherwise the guest falls back to
# English and answers a non-English host in the wrong language.
DIALOGUE_DEFAULTS = {
    "English": ["en-US-AvaNeural", "en-US-AndrewNeural"],
    "Chinese": ["zh-CN-XiaoxiaoNeural", "zh-CN-YunxiNeural"],
    "中文": ["zh-CN-XiaoxiaoNeural", "zh-CN-YunxiNeural"],
    "French": ["fr-FR-DeniseNeural", "fr-FR-HenriNeural"],
    "German": ["de-DE-KatjaNeural", "de-DE-ConradNeural"],
    "Spanish": ["es-ES-ElviraNeural", "es-ES-AlvaroNeural"],
    "Portuguese": ["pt-BR-FranciscaNeural", "pt-BR-AntonioNeural"],
    "Japanese": ["ja-JP-NanamiNeural", "ja-JP-KeitaNeural"],
}


def _default_voice(language: str, idx: int) -> str:
    pair = DIALOGUE_DEFAULTS.get(language)
    if pair:
        return pair[idx]
    # unknown language: host keeps the single-voice pick, guest falls back to English
    return EDGE_VOICES.get(language, "en-US-AriaNeural") if idx == 0 else "en-US-GuyNeural"


async def synthesize(s: Settings, text: str, language: str = "English", voice: str = "",
                     sections: list[str] | None = None) -> dict:
    """Synthesize `text`. If `sections` is given, each is synthesized separately and
    its measured duration reported, so chapter offsets are real rather than guessed.
    edge-tts emits headerless CBR mp3 frames, so concatenating the parts yields a
    file whose measured length equals the sum of the parts exactly."""
    if s.tts_engine == "api":
        return {**await _synth_api(s, text), "sections": []}

    parts = [p for p in (sections or [text]) if p.strip()]
    audio = bytearray()
    durations: list[float] = []
    for part in parts:
        chunk = await _edge_bytes(s, part, voice, language)
        if not chunk:
            continue
        audio.extend(chunk)
        durations.append(_mp3_duration(chunk))
    data = bytes(audio)
    if not data:
        raise RuntimeError("TTS 合成结果为空")
    return {"audio": data, "ext": "mp3", "duration": round(sum(durations), 1),
            "sections": durations}


async def synthesize_dialogue(s: Settings, segments: list[dict], language: str = "English",
                              host_voice: str = "", guest_voice: str = "") -> dict:
    # API engine has a single voice: read the joined text in one voice (no labels).
    if s.tts_engine == "api":
        joined = "\n".join(seg["text"] for seg in segments)
        return {**await _synth_api(s, joined), "sections": []}

    host_voice = host_voice or _default_voice(language, 0)
    guest_voice = guest_voice or _default_voice(language, 1)
    audio = bytearray()
    per_section: dict[int, float] = {}
    for seg in segments:
        v = host_voice if seg.get("speaker") == "host" else guest_voice
        part = await _edge_bytes(s, seg["text"], v, language)
        if part:
            audio.extend(part)
            idx = seg.get("section", 0)
            per_section[idx] = per_section.get(idx, 0.0) + _mp3_duration(part)
    data = bytes(audio)
    if not data:
        raise RuntimeError("对谈语音合成为空")
    sections = [per_section.get(i, 0.0) for i in range(max(per_section, default=-1) + 1)]
    return {"audio": data, "ext": "mp3", "duration": round(sum(sections), 1),
            "sections": sections}


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
    return {"audio": data, "ext": "mp3", "duration": round(_mp3_duration(data), 1)}


def _mp3_duration(b: bytes) -> float:
    from mutagen.mp3 import MP3

    return MP3(io.BytesIO(b)).info.length
