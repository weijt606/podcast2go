"""Pluggable engines for TTS / STT / search / extract.

Each capability is a single module exposing one async entry point. The bundled
implementations are free / open-source and need no API key:

- tts.py     -> edge-tts
- search.py  -> DuckDuckGo
- extract.py -> trafilatura
- stt.py     -> faster-whisper (optional dep)

To plug in a paid/managed API (e.g. an LLM-grade TTS, a search API, a hosted
extractor), add a branch in the relevant module — the call sites and Settings
flow are already wired for it.
"""
