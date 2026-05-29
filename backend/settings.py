"""Per-request settings (BYOK): request overrides on top of server .env defaults.

The frontend may send its own LLM endpoint/key/model with each /api/generate
call. Anything not provided falls back to the values in config.py (backend/.env).
"""
from dataclasses import dataclass

import config as env


@dataclass
class Settings:
    llm_api_key: str
    llm_base_url: str
    llm_model: str
    edge_voice: str
    whisper_model: str
    wpm: int


def _g(o: dict, key: str, default: str) -> str:
    v = o.get(key)
    return v.strip() if isinstance(v, str) and v.strip() else default


def resolve(o: dict) -> Settings:
    return Settings(
        llm_api_key=_g(o, "llm_api_key", env.LLM_API_KEY),
        llm_base_url=_g(o, "llm_base_url", env.LLM_BASE_URL),
        llm_model=_g(o, "llm_model", env.LLM_MODEL),
        edge_voice=_g(o, "edge_voice", env.EDGE_VOICE),
        whisper_model=_g(o, "whisper_model", env.WHISPER_MODEL),
        wpm=int(o.get("wpm") or env.WPM),
    )
