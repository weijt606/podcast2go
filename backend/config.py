import os

from dotenv import load_dotenv

load_dotenv()  # reads backend/.env when uvicorn runs from backend/

NEBIUS_API_KEY = os.getenv("NEBIUS_API_KEY", "")
NEBIUS_BASE_URL = os.getenv("NEBIUS_BASE_URL", "https://api.studio.nebius.ai/v1")
NEBIUS_MODEL = os.getenv("NEBIUS_MODEL", "deepseek-ai/DeepSeek-V3")

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

GRADIUM_API_KEY = os.getenv("GRADIUM_API_KEY", "")
GRADIUM_BASE_URL = os.getenv("GRADIUM_BASE_URL", "")  # optional region override
GRADIUM_VOICE_ID = os.getenv("GRADIUM_VOICE_ID", "YTpq7expH9539ERJ")

WPM = int(os.getenv("WPM", "150"))
