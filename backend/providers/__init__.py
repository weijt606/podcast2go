"""Pluggable engines for TTS / STT / search / extract.

Each capability is a single module exposing one async entry point that
dispatches on a *_PROVIDER env var (see config.py). Open-source / free
implementations are the defaults; Gradium and Tavily are opt-in.
"""
