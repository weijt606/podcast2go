"""LLM: long text -> ranked key points (map-reduce for long inputs)."""
from settings import Settings

from .llm import chat, safe_json

CHUNK = 24000  # chars per map chunk (~6k tokens)


def _chunks(text: str, size: int = CHUNK):
    return [text[i:i + size] for i in range(0, len(text), size)] or [""]


async def extract_key_points(s: Settings, title: str, text: str, focus: str = "") -> dict:
    focus_hint = f" Prioritize anything related to: {focus}." if focus.strip() else ""
    chunks = _chunks(text)

    # --- map: pull raw bullet points from each chunk ---
    bullets: list[str] = []
    for i, c in enumerate(chunks):
        out = await chat(
            s,
            'You extract factual, self-contained bullet points from a transcript/article '
            'chunk. Return JSON {"points": ["...", "..."]}. No commentary.',
            f'Source: "{title}" (chunk {i + 1}/{len(chunks)}).{focus_hint}\n\n{c}',
        )
        bullets.extend(safe_json(out).get("points", []))

    # --- reduce: dedupe, rank, attach why-it-matters ---
    joined = "\n".join(f"- {b}" for b in bullets)
    out = await chat(
        s,
        "You are an editor. From these raw bullets, produce the key points a busy "
        "listener must know. Merge duplicates, rank by importance. Return JSON "
        '{"summary": "2-sentence overview", "key_points": '
        '[{"point": "short claim", "detail": "1-2 sentences", "importance": 1-5}]}. '
        "Return at most 8 key points." + (f" Bias toward: {focus}." if focus.strip() else ""),
        f'Source: "{title}".\n\nRaw bullets:\n{joined}',
    )
    data = safe_json(out)
    if not data.get("key_points"):
        data = {
            "summary": title,
            "key_points": [{"point": b, "detail": "", "importance": 3} for b in bullets[:8]],
        }
    return data
