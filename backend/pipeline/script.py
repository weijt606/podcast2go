"""LLM: key points + research -> a time-budgeted spoken podcast script.

mode="single"   -> one-host monologue (natural, spoken style).
mode="dialogue" -> two-host back-and-forth; returns `segments` for per-voice TTS.

The model separates chapters with a SECTION marker line. Splitting on it lets the
TTS stage synthesize and measure each chapter, so the player's chapter jumps land
on the real offsets instead of an even split. If the model ignores the marker the
split simply collapses to one section and the caller falls back to the estimate.
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
    "值得注意的是 / 在这个…的时代 / 总之 / 归根结底 / 说到底 / 总的来说'.\n"
    "- No symmetrical 'not only X but also Y' / '不仅…而且 / 既…又…', no hedging ('arguably / it "
    "could be said' / '某种程度上'), no restating the same idea, no pre-announcing structure "
    "('here are three reasons' / '下面三点').\n"
    "- Prefer concrete specifics and plain active verbs over abstraction and passive 'be / seem / "
    "appear' / 被字句、对…进行…; drop the '们' on abstractions and stacked 四字成语.\n"
    "- Vary sentence length, use contractions and natural spoken transitions, and let a real opinion "
    "show.\n"
    "- End on the last concrete thing you have to say, then stop. No summary sentence, no "
    "widening out to the industry / the era / what this means for all of us, no line addressed to "
    "the listener about where they now stand. If the final sentence would still make sense attached "
    "to a different episode, cut it.\n"
    "- Never write em-dashes (—/——), the ellipsis character …, or arrows/bullets (→ • ·): use words "
    "a host would actually say aloud.\n"
    "Keep every fact unchanged."
)


# Spoken Chinese/Japanese runs ~240 characters per minute against ~150 English words,
# and those scripts are counted in characters, not whitespace tokens. Measured: a 738-char
# Chinese script synthesized to 189.6s, i.e. 233 chars/min.
CJK_CHARS_PER_MIN = 240
_CJK = re.compile(r"[\u3400-\u9fff\u3040-\u30ff]")
_LATIN_WORD = re.compile(r"[A-Za-z0-9]+")


def _is_cjk(language: str) -> bool:
    return language.startswith(("中", "Chinese", "日", "Japanese"))


def count_units(text: str) -> int:
    """Script length in the unit the language is budgeted in: CJK characters plus
    whitespace-delimited Latin words. `text.split()` reports 6 for a 900-char Chinese
    script, which is useless both as progress and as a budget check."""
    return len(_CJK.findall(text)) + len(_LATIN_WORD.findall(text))


def length_unit(language: str) -> str:
    return "characters" if _is_cjk(language) else "words"


def _budget(minutes: int, wpm: int, language: str) -> tuple[int, str]:
    if _is_cjk(language):
        return int(minutes * CJK_CHARS_PER_MIN), "characters"
    return int(minutes * wpm), "words"


SECTION = "[[SECTION]]"
_SECTION_LINE = re.compile(r"^\s*\[\[SECTION\]\]\s*$", re.M)


def _split_sections(text: str) -> list[str]:
    parts = [p.strip() for p in _SECTION_LINE.split(text)]
    return [p for p in parts if p]


def _labels(language: str) -> dict:
    zh = language.startswith(("中", "Chinese"))
    return {"host": "主播" if zh else "Host", "guest": "嘉宾" if zh else "Guest"}


def _parse_dialogue(raw: str) -> list[dict]:
    """Parse 'HOST:/GUEST:'-tagged lines into ordered speaker segments."""
    segs: list[dict] = []
    section = 0
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if line == SECTION:
            section += 1
            continue
        m = re.match(r"^(HOST|GUEST)\s*[:：]\s*(.*)$", line, re.I)
        if m:
            speaker = "host" if m.group(1).lower() == "host" else "guest"
            txt = m.group(2).strip()
            if txt:
                segs.append({"speaker": speaker, "text": txt, "section": section})
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
    budget, unit = _budget(minutes, s.wpm, language)

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
        f"TARGET LENGTH: about {budget} {unit} of spoken {language} (~{minutes} min). "
        f"Stay within +/-10% of {budget} {unit}.\n\n"
        f"Key points (priority in parentheses):\n{kp}\n\n"
        f"Deep-dive research to weave in:\n{rs}"
    )
    chapters = [{"title": p["point"]} for p in key_points[:5]]
    # asking for one marker between consecutive chapters gives the TTS stage a real
    # boundary to measure; blank when there is only one chapter to separate
    marker_rule = (
        f"\n\nPut a line containing only {SECTION} between consecutive key points "
        f"({len(chapters) - 1} such lines in total, one per boundary). It is a silent "
        f"separator: never speak it, never mention it, never add anything else to that line."
        if len(chapters) > 1 else ""
    )

    if mode == "dialogue":
        # Left to itself the model writes very short turns and stops early: measured
        # -30% to -47% against the budget on 3-min Chinese dialogues (deepseek-chat).
        # Turn count was never the problem, turn length was, so compute both and state
        # them. This pulls the mean to about -28% but not the spread (-8% to -40% across
        # runs), which is why the README calls dialogue length approximate and points
        # anyone who needs an accurate duration at single-host mode.
        per_turn = 55 if _is_cjk(language) else 35
        turns = max(8, round(budget / per_turn))
        system = (
            f"You are scripting a two-person podcast in {language}. Two speakers: HOST and GUEST. "
            f"Every line MUST begin with 'HOST:' or 'GUEST:' (these exact English tags) followed by "
            f"that speaker's words in {language}. Make it a natural, lively back-and-forth: short "
            f"turns, genuine reactions, questions and answers, the way two people actually talk on a "
            f"podcast, not a lecture. The HOST guides; the GUEST explains the key points and research. "
            f"No markdown, no stage directions, no emoji, no preamble."
        ) + "\n\n" + HUMAN_VOICE
        user = context + (
            f"\n\nTotal budget ~{budget} {unit} across BOTH speakers combined. That is about "
            f"{turns} turns of roughly {per_turn} {unit} each: a turn is a few full sentences, "
            f"not a one-line reaction. Keep going until you have spent the whole budget. "
            f"Running short is a failure even if the conversation feels finished.\n"
            f"Open with a short hook from the HOST, cover the key points in priority order, "
            f"and end with a quick wrap-up."
        ) + marker_rule
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
        f"sentence length, light connective phrases, warm and human, not a stiff written essay. "
        f"Output ONLY the spoken text: no markdown, no headers, no bullet symbols, no stage "
        f"directions, no emoji, and no preamble such as 'Here is'. Open with a one-line hook, cover "
        f"the key points in priority order weaving in the research naturally, and close with a short "
        f"takeaway."
    ) + "\n\n" + HUMAN_VOICE
    text = await chat(s, system, context + marker_rule, json_mode=False, temperature=0.6)
    script = re.sub(r"^```.*?\n|```$", "", text.strip(), flags=re.DOTALL).strip()
    if not script:
        raise RuntimeError("脚本生成为空（检查 LLM model 是否有效）")
    sections = _split_sections(script)
    return {"script": "\n\n".join(sections), "chapters": chapters,
            "segments": None, "sections": sections}
