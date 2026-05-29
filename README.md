# 🎧 podcast2go

[![English](https://img.shields.io/badge/lang-English-2563eb?style=flat-square)](README.md)
[![简体中文](https://img.shields.io/badge/lang-简体中文-gray?style=flat-square)](README.zh-CN.md)

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

1. **Ingest** — articles (trafilatura), YouTube (captions), or audio/podcast URLs (Whisper STT)
2. **Extract** — an LLM distills the long text into ranked key points
3. **Research** — the top points are searched on the web for background and sources
4. **Script** — a length-budgeted spoken script (`target minutes × words-per-minute`)
5. **Synthesize** — TTS renders the audio; the UI supports lock-screen background playback

### Features

- ⏱️ **Time-controlled** output (3 / 5 / 10 / 15 min) via a deterministic word budget
- 🎛️ **Steerable**: focus topics, deep-dive topics, tone/angle, output language
- 🌍 **Multi-language** audio (incl. Chinese) via edge-tts
- 📱 Mobile PWA with **background playback** (Media Session API)
- 🌐 **Bilingual UI** (English / 简体中文) toggle
- 🔑 **BYOK** — bring your own LLM endpoint/key from the UI or `.env`

## Engines (all swappable)

Bundled engines are free / open-source and need **no API key**. The architecture is
pluggable — to use a managed API instead, add a branch in the matching `providers/*.py`.

| Capability | Bundled (free) | Recommended alternatives you can plug in |
|---|---|---|
| **LLM** | any OpenAI-compatible endpoint | OpenAI · Groq · Together · OpenRouter · Nebius · local **Ollama** |
| **TTS** | edge-tts (multi-language incl. Chinese) | OpenAI TTS · ElevenLabs · Azure · Piper (offline) |
| **Web search** | DuckDuckGo (`ddgs`) | Tavily · Brave · Serper |
| **Article extract** | trafilatura | Tavily Extract · Mercury · Readability |
| **STT** (audio sources) | faster-whisper | — |

## Quickstart

Requires **Python ≥ 3.10**.

```bash
git clone https://github.com/weijt606/podcast2go.git
cd podcast2go

cp .env.example backend/.env          # set ONE LLM endpoint (see below)

cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
# open http://localhost:8000
```

### Configure the LLM (the only required key)

Edit `backend/.env` and point it at any OpenAI-compatible endpoint, e.g.:

```bash
# Hosted (pick one)
LLM_BASE_URL=https://api.openai.com/v1      LLM_API_KEY=sk-...   LLM_MODEL=gpt-4o-mini
LLM_BASE_URL=https://api.groq.com/openai/v1 LLM_API_KEY=gsk_...  LLM_MODEL=llama-3.3-70b-versatile

# Fully local & free (no key) — install Ollama, `ollama pull llama3.1`, then:
LLM_BASE_URL=http://localhost:11434/v1      LLM_API_KEY=ollama   LLM_MODEL=llama3.1
```

You can also set the LLM endpoint per-session from the UI's ⚙️ panel (stored in your browser).
To transcribe audio/podcast URLs, also `pip install faster-whisper`.

## Notes

- Generated audio defaults to English; switch output language in the UI (edge-tts supports Chinese, Japanese, and several European languages).
- State is in-memory and single-process — this is a personal/self-hosted tool, not a multi-tenant service.

See [CLAUDE.md](./CLAUDE.md) for architecture and build details.
