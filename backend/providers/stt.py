"""Speech-to-text for audio/podcast URLs: url -> transcript text.

Open-source via faster-whisper (optional dep: `pip install faster-whisper`).
Models are loaded lazily and cached per model name, so importing is free.
"""
import asyncio
import os
import tempfile
import urllib.request

from settings import Settings

_models: dict = {}


def _load(model_name: str):
    if model_name not in _models:
        try:
            from faster_whisper import WhisperModel
        except ImportError as e:
            raise RuntimeError("音频来源需要 STT：请先 `pip install faster-whisper`") from e
        _models[model_name] = WhisperModel(model_name, device="cpu", compute_type="int8")
    return _models[model_name]


async def transcribe(s: Settings, url: str) -> str:
    return await asyncio.to_thread(_transcribe_sync, s.whisper_model, url)


def _transcribe_sync(model_name: str, url: str) -> str:
    model = _load(model_name)
    fd, path = tempfile.mkstemp(suffix=".audio")
    os.close(fd)
    try:
        urllib.request.urlretrieve(url, path)
        segments, _info = model.transcribe(path)
        text = " ".join(seg.text.strip() for seg in segments).strip()
        if not text:
            raise RuntimeError("音频转写结果为空")
        return text
    finally:
        if os.path.exists(path):
            os.unlink(path)
