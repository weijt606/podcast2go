"""OpenAI-compatible LLM wrapper. Client is built from per-request Settings."""
import json
import re

from openai import AsyncOpenAI

from settings import Settings

_clients: dict[tuple, AsyncOpenAI] = {}


def _client(s: Settings) -> AsyncOpenAI:
    key = (s.llm_base_url, s.llm_api_key)
    if key not in _clients:
        if not s.llm_api_key:
            raise RuntimeError("LLM API key 未设置（在前端设置里填入，或配置 backend/.env）")
        _clients[key] = AsyncOpenAI(base_url=s.llm_base_url, api_key=s.llm_api_key)
    return _clients[key]


async def chat(s: Settings, system: str, user: str, json_mode: bool = True, temperature: float = 0.3) -> str:
    client = _client(s)
    msgs = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    try:
        kw = {"response_format": {"type": "json_object"}} if json_mode else {}
        r = await client.chat.completions.create(
            model=s.llm_model, messages=msgs, temperature=temperature, **kw
        )
    except Exception:
        r = await client.chat.completions.create(
            model=s.llm_model, messages=msgs, temperature=temperature
        )
    return r.choices[0].message.content


def safe_json(s: str) -> dict:
    s = s.strip()
    s = re.sub(r"^```(?:json)?|```$", "", s, flags=re.MULTILINE).strip()
    try:
        return json.loads(s)
    except Exception:
        m = re.search(r"\{.*\}", s, re.DOTALL)
        return json.loads(m.group(0)) if m else {}
