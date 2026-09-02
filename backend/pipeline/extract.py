"""LLM: long text -> ranked key points (map-reduce for long inputs)."""
import asyncio

from settings import Settings

from .llm import chat, safe_json

CHUNK = 24000    # chars per map chunk (~6k tokens)
MAP_CONCURRENCY = 4  # a full episode is 8-12 chunks; keep free-tier rate limits happy


def _chunks(text: str, size: int = CHUNK):
    return [text[i:i + size] for i in range(0, len(text), size)] or [""]


async def extract_key_points(s: Settings, title: str, text: str, focus: str = "",
                             language: str = "English") -> dict:
    """Map-reduce a long source into ranked key points.

    The map step stays in the source language so nothing is lost in translation. The
    reduce step writes in `language`, because its output is what the listener sees:
    the chapter titles and the key-point panel next to the player.
    """
    focus_hint = f" Prioritize anything related to: {focus}." if focus.strip() else ""
    chunks = _chunks(text)

    # --- map: pull raw bullet points from each chunk, concurrently ---
    sem = asyncio.Semaphore(MAP_CONCURRENCY)

    async def map_chunk(i: int, c: str) -> list[str]:
        async with sem:
            out = await chat(
                s,
                'You extract factual, self-contained bullet points from a transcript/article '
                'chunk. Return JSON {"points": ["...", "..."]}. No commentary.',
                f'Source: "{title}" (chunk {i + 1}/{len(chunks)}).{focus_hint}\n\n{c}',
            )
        return safe_json(out).get("points", [])

    mapped = await asyncio.gather(*[map_chunk(i, c) for i, c in enumerate(chunks)])
    bullets: list[str] = [b for part in mapped for b in part]  # source order preserved

    # --- reduce: dedupe, rank, attach why-it-matters ---
    joined = "\n".join(f"- {b}" for b in bullets)
    out = await chat(
        s,
        "You are an editor. From these raw bullets, produce the key points a busy "
        "listener must know. Merge duplicates, rank by importance. Return JSON "
        '{"summary": "2-sentence overview", "key_points": '
        '[{"point": "short claim", "detail": "1-2 sentences", "importance": 1-5}]}. '
        "Return at most 8 key points. "
        f'Write every "summary", "point" and "detail" value in {language}, whatever '
        "language the bullets are in: they become the chapter titles and the key-point "
        "list the listener reads."
        + (f" Bias toward: {focus}." if focus.strip() else ""),
        f'Source: "{title}".\n\nRaw bullets:\n{joined}',
    )
    data = safe_json(out)
    if not data.get("key_points"):
        data = {
            "summary": title,
            "key_points": [{"point": b, "detail": "", "importance": 3} for b in bullets[:8]],
        }
    return data
