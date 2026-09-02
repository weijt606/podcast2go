"""Speech-to-text for audio/podcast URLs: url -> transcript text.

Open-source via faster-whisper (optional dep: `pip install faster-whisper`).
Models are loaded lazily and cached per model name, so importing is free.
"""
import asyncio
import os
import tempfile
import urllib.request

from settings import Settings

DOWNLOAD_TIMEOUT = 60        # seconds to first byte / between reads
MAX_AUDIO_BYTES = 400 << 20  # 400 MB: a long episode is ~100 MB, a bad link is unbounded
_UA = "Mozilla/5.0 (podcast2go)"

_models: dict = {}


def _load(model_name: str):
    if model_name not in _models:
        try:
            from faster_whisper import WhisperModel
        except ImportError as e:
            raise RuntimeError("音频来源需要 STT：请先 `pip install faster-whisper`") from e
        _models[model_name] = WhisperModel(model_name, device="cpu", compute_type="int8")
    return _models[model_name]


async def transcribe(s: Settings, url: str, on_progress=None) -> str:
    """Download and transcribe. `on_progress(key, **args)` reports the stage, since
    whisper on CPU can run for many minutes with nothing else to show the user."""
    return await asyncio.to_thread(_transcribe_sync, s.whisper_model, url, on_progress)


def _download(url: str, path: str) -> int:
    """Stream to `path` with a timeout and a size cap. urlretrieve has neither."""
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    size = 0
    with urllib.request.urlopen(req, timeout=DOWNLOAD_TIMEOUT) as r, open(path, "wb") as f:
        while True:
            block = r.read(1 << 16)
            if not block:
                break
            size += len(block)
            if size > MAX_AUDIO_BYTES:
                raise RuntimeError(
                    f"音频超过 {MAX_AUDIO_BYTES >> 20} MB 上限，已中止下载")
            f.write(block)
    if not size:
        raise RuntimeError("音频下载为空")
    return size


def _transcribe_sync(model_name: str, url: str, on_progress=None) -> str:
    def report(key, **args):
        if on_progress:
            on_progress(key, **args)

    model = _load(model_name)
    fd, path = tempfile.mkstemp(suffix=".audio")
    os.close(fd)
    try:
        report("stt_download")
        size = _download(url, path)
        report("stt_transcribe", mb=round(size / (1 << 20)))
        segments, _info = model.transcribe(path)
        text = " ".join(seg.text.strip() for seg in segments).strip()
        if not text:
            raise RuntimeError("音频转写结果为空")
        return text
    finally:
        if os.path.exists(path):
            os.unlink(path)
