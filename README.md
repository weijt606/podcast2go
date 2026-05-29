# 🎧 podcast2go

[![English](https://img.shields.io/badge/lang-English-2563eb?style=flat-square)](README.md)
[![简体中文](https://img.shields.io/badge/lang-简体中文-gray?style=flat-square)](README.zh-CN.md)

> Turn a long podcast / video / article into a **time-boxed, key-point-focused audio digest enriched with deep search** — built for listening on the go: commuting, running, walking, driving.

## What it solves

Long content (an hour-long podcast, a multi-thousand-word article) is hard to digest in spare moments. Paste a link, pick a target duration, and podcast2go gives you back an audio digest that runs for exactly that long, covers only the key points, and weaves in supporting background — put your earbuds in and you're done.

## How it works

1. **Ingest** — articles via Tavily Extract; YouTube via captions
2. **Extract** — an LLM on Nebius distills long text into ranked key points
3. **Deep research** — Tavily searches the most important points for background and sources
4. **Script** — a length-budgeted spoken script (`target minutes × words-per-minute`)
5. **Synthesize** — Gradium TTS renders the audio; the UI supports lock-screen background playback

## Tech stack

- **Backend / pipeline**: Python + FastAPI (single service, no DB)
- **LLM**: Nebius AI Studio (OpenAI-compatible)
- **Search / extraction**: Tavily (Search + Extract)
- **Text-to-speech**: Gradium TTS
- **Frontend**: mobile single-page (Tailwind CDN + PWA), served directly by FastAPI

## Quick start

```bash
cp .env.example backend/.env        # fill in NEBIUS / TAVILY / GRADIUM keys
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
open http://localhost:8000
```

> ⚠️ Gradium TTS currently supports English / French / German / Spanish / Portuguese — **not Chinese**. Source content can be in any language, but the generated audio defaults to English.

See [CLAUDE.md](./CLAUDE.md) for build/run details and conventions.
