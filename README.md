# 🎧 podcast2go

![podcast2go — a four-panel black-and-white comic: a commuter overwhelmed by a 1-hour video and an endless article, pastes the link and picks a 5-min length, a friendly machine turns the long pile into a short audio digest, then they walk off listening on earbuds](./podcast2go-banner-en.png)

[![English](https://img.shields.io/badge/README-English-15803d?style=flat-square)](README.md)
[![简体中文](https://img.shields.io/badge/README-简体中文-1f6feb?style=flat-square)](README.zh-CN.md)
[![Python](https://img.shields.io/badge/Python-3.10+-111111?style=flat-square)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-backend-111111?style=flat-square)](https://fastapi.tiangolo.com/)
![Engines](https://img.shields.io/badge/engines-free%20%2F%20no%20key-orange?style=flat-square)
![PWA](https://img.shields.io/badge/PWA-background%20audio-1f6feb?style=flat-square)

> Turn a long podcast / video / article into a **time-boxed, key-point-focused audio digest enriched with web research** — built for listening on the go: commuting, running, walking, driving.

## What it is

Long content (an hour-long podcast, a multi-thousand-word article) is hard to digest in
spare moments. With podcast2go you paste a link and pick a target duration, and it returns
an audio digest that runs for *about that long*, covers only the key points, and weaves in
supporting background from the web. Put your earbuds in and you're done.

It's a small, self-hosted FastAPI app with a mobile web UI. It is **vendor-neutral** and
runs on **free / open-source engines out of the box** — the only thing you bring is an LLM
endpoint (and that can be a local one).

### How it works

```
link ─▶ ingest ─▶ extract key points ─▶ web research ─▶ time-boxed script ─▶ TTS ─▶ 🎧
```

1. **Ingest** — articles (trafilatura), YouTube (captions), **Apple Podcasts / RSS / 小宇宙**, or audio URLs (Whisper STT)
2. **Extract** — an LLM distills the long text into ranked key points
3. **Research** — the top points are searched on the web for background and sources
4. **Script** — a length-budgeted spoken script (`target minutes × words-per-minute`), written in a natural human voice (anti-vibe-writing rules), as a monologue or a two-host dialogue
5. **Synthesize** — TTS renders the audio; the UI supports lock-screen background playback

### Features

- ⏱️ **Time-controlled** output (3 / 5 / 10 / 15 min) via a deterministic word budget
- 🎙️ **Two formats**: single-host narration or **two-host dialogue** (each speaker its own voice)
- 🗣️ **Voice picker with preview** — curated edge-tts voices per language, or a custom TTS API
- 🧑 **Human-sounding scripts** — anti-vibe-writing rules strip the AI-writing flavor (EN / 中文)
- 📻 **Podcast & audio ingestion** — Apple Podcasts, RSS feeds, 小宇宙, YouTube, articles, audio files (with a one-tap **link check**)
- 🎛️ **Steerable**: focus topics, deep-dive topics, tone/angle, output language
- 🌍 **Multi-language** audio (incl. Chinese) via edge-tts
- 🔌 **Connectivity test** buttons for the LLM and TTS endpoints
- 📱 Mobile PWA with **background playback** (Media Session API)
- 🌐 **Bilingual UI** (English / 简体中文) toggle
- 🔑 **BYOK** — bring your own LLM / TTS endpoint & key from the UI or `.env`

## Screenshots

<table>
  <tr>
    <td align="center"><b>Home</b></td>
    <td align="center"><b>Advanced &amp; settings</b></td>
  </tr>
  <tr>
    <td valign="top"><img src="./docs/screenshot-home.png" width="300" alt="podcast2go home: paste a link, pick a length" /></td>
    <td valign="top"><img src="./docs/screenshot-advanced.png" width="300" alt="advanced & settings: LLM/TTS test buttons, TTS engine choice, mode, voice picker with preview" /></td>
  </tr>
</table>

Home (paste a link, pick a length) · advanced &amp; settings (LLM/TTS test buttons, TTS engine
choice, single/dialogue mode, voice picker with **▶ Preview**).

## Engines (all swappable)

The engines this project ships with are free / open-source and need **no API key**. The
architecture is pluggable — to use a managed API instead, add a branch in the matching `providers/*.py`.

| Capability | Used by this project | Recommended alternatives you can plug in |
|---|---|---|
| **LLM** | any OpenAI-compatible endpoint | OpenAI · Groq · OpenRouter · DeepSeek · Zhipu GLM · Qwen · Moonshot (Kimi) · local **Ollama** |
| **TTS** | edge-tts (multi-language incl. Chinese) | OpenAI TTS · ElevenLabs · Piper (offline) · [CosyVoice](https://github.com/FunAudioLLM/CosyVoice) (Alibaba, open-source) · [VoxCPM](https://github.com/OpenBMB/VoxCPM) (local, voice cloning) |
| **Web search** | DuckDuckGo (`ddgs`) | Tavily · Brave · Serper · LLM/agent-native web search |
| **Article extract** | trafilatura | Tavily Extract · Mercury · Readability |
| **STT** (audio sources) | faster-whisper | — |

### Voice synthesis (TTS)

The voice engine this project uses is [**edge-tts**](https://github.com/rany2/edge-tts) — Microsoft Edge's
online neural voices. It's **free, needs no API key**, and outputs **mp3** (`backend/providers/tts.py`).

- **Pick a voice, preview it, choose a format.** Advanced options let you select the narrator
  voice from a curated list of natural voices and hit **▶ Preview** to hear a sample, and switch
  between single-host narration and two-host **dialogue** (each speaker gets its own voice). The
  LLM endpoint and a custom TTS API are both **testable** from the settings panel.
- **Voice is auto-picked from the output language.** English, Chinese, Japanese, French, German,
  Spanish, and Portuguese each map to a default neural voice (e.g. `en-US-AriaNeural`,
  `zh-CN-XiaoxiaoNeural`); anything else falls back to English. Pin a specific voice with
  `EDGE_VOICE=` in `backend/.env` (or per-session from the UI).
- **Online, not offline.** edge-tts streams from Microsoft's service, so synthesis needs an
  internet connection — it isn't a local/offline voice. For local/offline audio, swap in
  **Piper** (lightweight, CPU) or **[VoxCPM](https://github.com/OpenBMB/VoxCPM)** (OpenBMB,
  Apache-2.0, open weights) — a compact local model with studio-quality output and zero-shot
  voice cloning (Chinese, English, and more); runs offline but needs an NVIDIA GPU.
- **Length is controlled by the script, not the voice.** The clip runs ~`target minutes` because
  the script step writes to a deterministic word budget (`minutes × WPM`, `WPM=150` by default).
  The actual mp3 length is then measured (via `mutagen`) and shown in the player.
- **Swap engines** by adding a branch in `backend/providers/tts.py` and returning the same
  `{audio, ext, duration}` shape — OpenAI TTS · ElevenLabs · Piper (offline) ·
  [CosyVoice](https://github.com/FunAudioLLM/CosyVoice) (Alibaba, open-source) ·
  [VoxCPM](https://github.com/OpenBMB/VoxCPM) (`pip install voxcpm`, local GPU).

## Quickstart

Requires **Python ≥ 3.10**.

```bash
git clone https://github.com/weijt606/podcast2go.git
cd podcast2go

cp .env.example backend/.env          # optional — or set the LLM in the app's BYOK panel

cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
# open http://localhost:8000
```

### Configure the LLM (the only required key)

Edit `backend/.env` and point it at any OpenAI-compatible endpoint, e.g.:

```bash
# Hosted (pick one) — domestic options first
LLM_BASE_URL=https://api.deepseek.com/v1          LLM_API_KEY=sk-...  LLM_MODEL=deepseek-chat
LLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4 LLM_API_KEY=...     LLM_MODEL=glm-4-flash
LLM_BASE_URL=https://api.openai.com/v1            LLM_API_KEY=sk-...  LLM_MODEL=gpt-4o-mini
LLM_BASE_URL=https://api.groq.com/openai/v1       LLM_API_KEY=gsk_... LLM_MODEL=llama-3.3-70b-versatile

# Fully local (no key) — install Ollama, `ollama pull llama3.1`, then:
LLM_BASE_URL=http://localhost:11434/v1            LLM_API_KEY=ollama  LLM_MODEL=llama3.1
```

You can also set the LLM endpoint per-session from the UI's settings panel (stored in your browser).

**Do I still need the `.env` file?** No — it's optional. `.env` only holds *server-side defaults*.
If you fill the Base URL / key / model in the app's BYOK settings panel, they're sent with each
request and take precedence, so you can run with **no `.env` at all**. Blank UI fields fall back to
`.env`. Use `.env` when you want a persistent default instead of re-typing it in each browser.

To ingest Apple Podcasts / RSS / 小宇宙 / audio URLs (which are transcribed with Whisper STT), also
`pip install faster-whisper`. (Spotify isn't supported — it exposes no open episode audio.)

## First-time guide

New here? This is the shortest path from zero to a finished audio digest — no paid API required.

**1 · Point it at an LLM.** podcast2go needs exactly one LLM endpoint — any OpenAI-compatible API
works (OpenAI, Groq, OpenRouter, DeepSeek, Zhipu GLM, …). Put the Base URL / key / model in `backend/.env`,
or straight into the app's BYOK settings panel — see
[Configure the LLM](#configure-the-llm-the-only-required-key).

*Optional, no-key alternative:* run a model locally with [Ollama](https://ollama.com):

```bash
# install Ollama from ollama.com, then:
ollama pull llama3.1
```

**2 · Install & run.** Follow [Quickstart](#quickstart) above (clone → `.env` → `pip install`
→ `uvicorn`). When the terminal prints `Uvicorn running on http://127.0.0.1:8000`, open that
address in your browser.

**3 · Make your first digest.**

1. Paste a **link** — article, YouTube, Apple Podcasts, an RSS feed, or 小宇宙 (tap **Check** to confirm it resolves).
2. Pick a **target length** (3 / 5 / 10 / 15 min).
3. *(optional)* Open **Advanced** for focus / deep-dive topics, tone, output language, single-host or two-host **mode**, and the **voice** (with **▶ Preview**).
4. Hit **Generate podcast** and watch the five steps run (parse → extract → research → script → voice).
5. When the player appears, press play — jump by chapter, skim the key points & sources, read the
   full script, or **Download** the mp3 to keep. Lock your phone and it keeps playing (background playback).

**4 · No `.env` key? Use the in-app panel.** Tap the settings panel at the top to paste an LLM
Base URL / key / model for this browser only — handy on a phone. Blank fields fall back to
`backend/.env`.

> Want to digest a podcast/audio link (Apple Podcasts, RSS, 小宇宙, audio files)? Run `pip install faster-whisper` once.

## Notes

- Generated audio defaults to English; switch output language in the UI (edge-tts supports Chinese, Japanese, and several European languages).
- State is in-memory and single-process — this is a personal/self-hosted tool, not a multi-tenant service.

See [CLAUDE.md](./CLAUDE.md) for architecture and build details.
