"""LLM: key points + research -> a time-budgeted spoken podcast script."""
from settings import Settings

from .llm import chat, safe_json


async def build_script(
    s: Settings,
    title: str,
    summary: str,
    key_points: list[dict],
    research: list[dict],
    minutes: int,
    prefs: str = "",
    language: str = "English",
) -> dict:
    budget = int(minutes * s.wpm)

    kp = "\n".join(
        f"- ({p.get('importance', 3)}/5) {p['point']}: {p.get('detail', '')}"
        for p in key_points
    )
    rs = "\n".join(
        f"- On '{r['point']}': {r['answer']}"
        for r in research if r.get("answer")
    ) or "(none)"

    system = (
        f"You are a podcast scriptwriter. Write a single-host spoken-word monologue in "
        f"{language}. It will be read aloud by a TTS engine, so: no markdown, no headers, "
        f"no bullet symbols, no stage directions, no emoji — only natural spoken sentences. "
        f"Open with a one-line hook, cover the key points in priority order weaving in the "
        f"research naturally, and close with a short takeaway. "
        f'Return JSON {{"script": "the full spoken text", '
        f'"chapters": [{{"title": "short chapter title"}}]}}.'
    )
    user = (
        f'Title: "{title}"\n'
        f"Overview: {summary}\n"
        f"Listener preference: {prefs or 'a general commuting audience'}\n"
        f"TARGET LENGTH: about {budget} words (~{minutes} min at {s.wpm} wpm). "
        f"Stay within +/-10% of {budget} words.\n\n"
        f"Key points (priority in parentheses):\n{kp}\n\n"
        f"Deep-dive research to weave in:\n{rs}"
    )
    data = safe_json(await chat(s, system, user, temperature=0.6))
    script = (data.get("script") or "").strip()
    if not script:
        raise RuntimeError("脚本生成为空（检查 LLM model 是否有效）")
    chapters = data.get("chapters") or [{"title": p["point"]} for p in key_points[:5]]
    return {"script": script, "chapters": chapters}
