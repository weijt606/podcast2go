"""Per-request settings (BYOK): request overrides on top of server .env defaults.

The frontend may send its own keys/providers with each /api/generate call.
Anything not provided falls back to the values in config.py (backend/.env).
"""
from dataclasses import dataclass

import config as env


@dataclass
class Settings:
    llm_api_key: str
    llm_base_url: str
    llm_model: str
    tts_provider: str
    search_provider: str
    extract_provider: str
    stt_provider: str
    gradium_api_key: str
    gradium_base_url: str
    gradium_voice_id: str
    tavily_api_key: str
    edge_voice: str
    whisper_model: str
    wpm: int


def _g(o: dict, key: str, default: str) -> str:
    v = o.get(key)
    return v.strip() if isinstance(v, str) and v.strip() else default


def resolve(o: dict) -> Settings:
    return Settings(
        llm_api_key=_g(o, "llm_api_key", env.NEBIUS_API_KEY),
        llm_base_url=_g(o, "llm_base_url", env.NEBIUS_BASE_URL),
        llm_model=_g(o, "llm_model", env.NEBIUS_MODEL),
        tts_provider=_g(o, "tts_provider", env.TTS_PROVIDER),
        search_provider=_g(o, "search_provider", env.SEARCH_PROVIDER),
        extract_provider=_g(o, "extract_provider", env.EXTRACT_PROVIDER),
        stt_provider=_g(o, "stt_provider", env.STT_PROVIDER),
        gradium_api_key=_g(o, "gradium_api_key", env.GRADIUM_API_KEY),
        gradium_base_url=_g(o, "gradium_base_url", env.GRADIUM_BASE_URL),
        gradium_voice_id=_g(o, "gradium_voice_id", env.GRADIUM_VOICE_ID),
        tavily_api_key=_g(o, "tavily_api_key", env.TAVILY_API_KEY),
        edge_voice=_g(o, "edge_voice", env.EDGE_VOICE),
        whisper_model=_g(o, "whisper_model", env.WHISPER_MODEL),
        wpm=int(o.get("wpm") or env.WPM),
    )
