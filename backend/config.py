import os

from dotenv import load_dotenv

load_dotenv()  # reads backend/.env when uvicorn runs from backend/

# ---- LLM (OpenAI-compatible: Nebius, or local Ollama at http://localhost:11434/v1) ----
NEBIUS_API_KEY = os.getenv("NEBIUS_API_KEY", "")
NEBIUS_BASE_URL = os.getenv("NEBIUS_BASE_URL", "https://api.studio.nebius.ai/v1")
NEBIUS_MODEL = os.getenv("NEBIUS_MODEL", "deepseek-ai/DeepSeek-V3")

# ---- Engine selection (open-source / free by default; paid tools opt-in) ----
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "edge")            # edge | gradium
SEARCH_PROVIDER = os.getenv("SEARCH_PROVIDER", "duckduckgo")  # duckduckgo | tavily
EXTRACT_PROVIDER = os.getenv("EXTRACT_PROVIDER", "trafilatura")  # trafilatura | tavily
STT_PROVIDER = os.getenv("STT_PROVIDER", "whisper")          # whisper

# ---- Tavily (only used when a provider above is set to "tavily") ----
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

# ---- Gradium (only used when TTS_PROVIDER=gradium) ----
GRADIUM_API_KEY = os.getenv("GRADIUM_API_KEY", "")
GRADIUM_BASE_URL = os.getenv("GRADIUM_BASE_URL", "")
GRADIUM_VOICE_ID = os.getenv("GRADIUM_VOICE_ID", "YTpq7expH9539ERJ")

# ---- edge-tts (free, no key, multi-language incl. Chinese) ----
EDGE_VOICE = os.getenv("EDGE_VOICE", "")  # override the auto voice-by-language

# ---- whisper STT (optional: pip install faster-whisper) ----
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")

WPM = int(os.getenv("WPM", "150"))
