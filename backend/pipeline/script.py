"""LLM: key points + research -> a time-budgeted spoken podcast script.

mode="single"   -> one-host monologue (natural, spoken style).
mode="dialogue" -> two-host back-and-forth; returns `segments` for per-voice TTS.
"""
import re

from settings import Settings

from .llm import chat

# Human-voice rules distilled from the anti-vibe-writing skill
# (github.com/weijt606/anti-vibe-writing) — strip the AI-writing flavor so the
# spoken script sounds like a real host, not generated prose.
HUMAN_VOICE = (
    "Sound like a real person talking, not AI-generated prose. Apply this in whatever the output "
    "language is:\n"
    "- Cut consultant-speak and filler: EN 'empower / unlock / leverage / let's dive in / in today's "
    "fast-paced world / it's important to note / in conclusion'; ZH '赋能 / 打通 / 落地 / 生态 / "
    "值得注意的是 / 在这个…的时代 / 总之 / 归根结底'.\n"
    "- No symmetrical 'not only X but also Y' / '不仅…而且 / 既…又…', no hedging ('arguably / it "
    "could be said' / '某种程度上'), no restating the same idea, no pre-announcing structure "
    "('here are three reasons' / '下面三点').\n"
    "- Prefer concrete specifics and plain active verbs over abstraction and passive 'be / seem / "
    "appear' / 被字句、对…进行…; drop the '们' on abstractions and stacked 四字成语.\n"
    "- Vary sentence length, use contractions and natural spoken transitions, and let a real opinion "
    "show. Don't end on hollow inspirational uplift.\n"
    "- Never write em-dashes (—/——), the ellipsis character …, or arrows/bullets (→ • ·): use words "
    "a host would actually say aloud.\n"
    "Keep every fact unchanged."
)


def _labels(language: str) -> dict:
    zh = language.startswith(("中", "Chinese"))
    return {"host": "主播" if zh else "Host", "guest": "嘉宾" if zh else "Guest"}


def _parse_dialogue(raw: str) -> list[dict]:
    """Parse 'HOST:/GUEST:'-tagged lines into ordered speaker segments."""
    segs: list[dict] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r"^(HOST|GUEST)\s*[:：]\s*(.*)$", line, re.I)
        if m:
            speaker = "host" if m.group(1).lower() == "host" else "guest"
            txt = m.group(2).strip()
            if txt:
                segs.append({"speaker": speaker, "text": txt})
        elif segs:  # untagged continuation line -> append to current speaker
            segs[-1]["text"] += " " + line
    return segs


async def build_script(
    s: Settings,
    title: str,
    summary: str,
    key_points: list[dict],
    research: list[dict],
    minutes: int,
    prefs: str = "",
    language: str = "English",
    mode: str = "single",
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

    context = (
        f'Title: "{title}"\n'
        f"Overview: {summary}\n"
        f"Listener preference: {prefs or 'a general commuting audience'}\n"
        f"TARGET LENGTH: about {budget} words (~{minutes} min at {s.wpm} wpm). "
        f"Stay within +/-10% of {budget} words.\n\n"
        f"Key points (priority in parentheses):\n{kp}\n\n"
        f"Deep-dive research to weave in:\n{rs}"
    )
    chapters = [{"title": p["point"]} for p in key_points[:5]]

    if mode == "dialogue":
        system = (
            f"You are scripting a two-person podcast in {language}. Two speakers: HOST and GUEST. "
            f"Every line MUST begin with 'HOST:' or 'GUEST:' (these exact English tags) followed by "
            f"that speaker's words in {language}. Make it a natural, lively back-and-forth — short "
            f"turns, genuine reactions, questions and answers, the way two people actually talk on a "
            f"podcast, not a lecture. The HOST guides; the GUEST explains the key points and research. "
            f"No markdown, no stage directions, no emoji, no preamble."
        ) + "\n\n" + HUMAN_VOICE
        user = context + (
            f"\n\nTotal budget ~{budget} words across BOTH speakers combined. "
            f"Open with a short hook from the HOST, cover the key points in priority order, "
            f"and end with a quick wrap-up."
        )
        text = await chat(s, system, user, json_mode=False, temperature=0.7)
        raw = re.sub(r"^```.*?\n|```$", "", text.strip(), flags=re.DOTALL).strip()
        segments = _parse_dialogue(raw)
        if segments:
            lab = _labels(language)
            display = "\n".join(f"{lab[seg['speaker']]}：{seg['text']}" for seg in segments)
            return {"script": display, "chapters": chapters, "segments": segments}
        # parsing failed -> fall back to reading the raw text single-voice
        if raw:
            return {"script": raw, "chapters": chapters, "segments": None}
        raise RuntimeError("对谈脚本生成为空（检查 LLM model 是否有效）")

    system = (
        f"You are a podcast scriptwriter. Write a single-host spoken monologue in {language}. "
        f"Write the way a real host actually talks out loud: natural rhythm, contractions, varied "
        f"sentence length, light connective phrases — warm and human, not a stiff written essay. "
        f"Output ONLY the spoken text — no markdown, no headers, no bullet symbols, no stage "
        f"directions, no emoji, and no preamble such as 'Here is'. Open with a one-line hook, cover "
        f"the key points in priority order weaving in the research naturally, and close with a short "
        f"takeaway."
    ) + "\n\n" + HUMAN_VOICE
    text = await chat(s, system, context, json_mode=False, temperature=0.6)
    script = re.sub(r"^```.*?\n|```$", "", text.strip(), flags=re.DOTALL).strip()
    if not script:
        raise RuntimeError("脚本生成为空（检查 LLM model 是否有效）")
    return {"script": script, "chapters": chapters, "segments": None}
