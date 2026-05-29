"""LLM: key points + research -> a time-budgeted spoken podcast script."""
import re

from settings import Settings

from .llm import chat


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
        f"{language}. Output ONLY the spoken text — no markdown, no headers, no bullet "
        f"symbols, no stage directions, no emoji, and no preamble such as 'Here is'. "
        f"Open with a one-line hook, cover the key points in priority order weaving in the "
        f"research naturally, and close with a short takeaway."
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
    # free-form prose, not JSON — embedding a long script in JSON is fragile for local models
    text = await chat(s, system, user, json_mode=False, temperature=0.6)
    script = re.sub(r"^```.*?\n|```$", "", text.strip(), flags=re.DOTALL).strip()
    if not script:
        raise RuntimeError("脚本生成为空（检查 LLM model 是否有效）")
    chapters = [{"title": p["point"]} for p in key_points[:5]]
    return {"script": script, "chapters": chapters}
