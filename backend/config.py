import os

from dotenv import load_dotenv

load_dotenv()  # reads backend/.env when uvicorn runs from backend/

# ---- LLM (any OpenAI-compatible endpoint) ----
# Works with OpenAI, Together, Groq, OpenRouter, Nebius, a local Ollama, etc.
# See .env.example for several recommended endpoints.
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

# ---- TTS: edge-tts (free, no key, multi-language incl. Chinese) ----
EDGE_VOICE = os.getenv("EDGE_VOICE", "")  # override the auto voice-by-language

# ---- STT for audio/podcast URLs: faster-whisper (open-source, optional dep) ----
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")

# Spoken words per minute used to compute the time budget.
WPM = int(os.getenv("WPM", "150"))
