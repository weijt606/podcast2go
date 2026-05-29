# 🎧 podcast2go

[![English](https://img.shields.io/badge/lang-English-2563eb?style=flat-square)](README.md)
[![简体中文](https://img.shields.io/badge/lang-简体中文-gray?style=flat-square)](README.zh-CN.md)

> Turn a long podcast / video / article into a **time-boxed, key-point-focused audio digest enriched with deep search** — built for listening on the go: commuting, running, walking, driving.

## What it solves

Long content (an hour-long podcast, a multi-thousand-word article) is hard to digest in spare moments. Paste a link, pick a target duration, and podcast2go gives you back an audio digest that runs for exactly that long, covers only the key points, and weaves in supporting background — put your earbuds in and you're done.

## How it works

1. **Ingest** — articles (trafilatura), YouTube (captions), or audio/podcast URLs (Whisper STT)
2. **Extract** — an LLM distills long text into ranked key points
3. **Deep research** — searches the most important points for background and sources
4. **Script** — a length-budgeted spoken script (`target minutes × words-per-minute`)
5. **Synthesize** — TTS renders the audio; the UI supports lock-screen background playback

## Pluggable engines

Every engine is swappable via env vars. Defaults are **free / open-source**, so the
only key you must provide is the LLM — paid tools are opt-in.

| Capability | Free default | Opt-in alternative |
|---|---|---|
| TTS | `edge-tts` (free, multi-language incl. Chinese) | Gradium (`TTS_PROVIDER=gradium`) |
| Web search | DuckDuckGo (`ddgs`) | Tavily (`SEARCH_PROVIDER=tavily`) |
| Article extract | trafilatura | Tavily (`EXTRACT_PROVIDER=tavily`) |
| STT (audio sources) | faster-whisper | — |
| LLM | any OpenAI-compatible (Nebius, or local Ollama) | — |

## Tech stack

- **Backend / pipeline**: Python + FastAPI (single service, no DB)
- **Frontend**: mobile single-page (Tailwind CDN + PWA), served directly by FastAPI

## Quick start

```bash
cp .env.example backend/.env        # set the LLM key (or point at local Ollama)
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
open http://localhost:8000
```

> 💡 With the default engines you need no paid keys — only an LLM endpoint (Nebius, or a
> local Ollama via `NEBIUS_BASE_URL=http://localhost:11434/v1`). Audio/podcast sources
> additionally need `pip install faster-whisper`.

## BYOK (bring your own key)

Keys and engine choices can be set **per request** from the UI's ⚙️ settings panel
(stored in your browser's localStorage, sent with each request) — or globally in
`backend/.env`. Request values win; anything blank falls back to `.env`.

See [CLAUDE.md](./CLAUDE.md) for build/run details and conventions.
