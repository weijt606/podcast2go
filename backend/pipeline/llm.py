"""Thin Nebius (OpenAI-compatible) wrapper shared by extract + script."""
import json
import re

from openai import AsyncOpenAI

from config import NEBIUS_API_KEY, NEBIUS_BASE_URL, NEBIUS_MODEL

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    # lazy so importing this module never requires a key (only calling chat() does)
    global _client
    if _client is None:
        if not NEBIUS_API_KEY:
            raise RuntimeError("NEBIUS_API_KEY 未设置（请在 backend/.env 配置）")
        _client = AsyncOpenAI(base_url=NEBIUS_BASE_URL, api_key=NEBIUS_API_KEY)
    return _client


async def chat(system: str, user: str, json_mode: bool = True, temperature: float = 0.3) -> str:
    client = _get_client()
    msgs = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    try:
        kw = {"response_format": {"type": "json_object"}} if json_mode else {}
        r = await client.chat.completions.create(
            model=NEBIUS_MODEL, messages=msgs, temperature=temperature, **kw
        )
    except Exception:
        # Some models reject response_format — retry without it (safe_json still parses).
        r = await client.chat.completions.create(
            model=NEBIUS_MODEL, messages=msgs, temperature=temperature
        )
    return r.choices[0].message.content


def safe_json(s: str) -> dict:
    """Parse model output that may be wrapped in code fences or prose."""
    s = s.strip()
    s = re.sub(r"^```(?:json)?|```$", "", s, flags=re.MULTILINE).strip()
    try:
        return json.loads(s)
    except Exception:
        m = re.search(r"\{.*\}", s, re.DOTALL)
        return json.loads(m.group(0)) if m else {}
