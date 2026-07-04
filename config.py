import os
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=env_path, override=True)

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "paper_trades.db")
CITIES = [
    {"name": "Hong Kong", "country": "HK", "lat": 22.3193, "lon": 114.1694, "market_keyword": "Hong Kong"},
    {"name": "Shanghai", "country": "CN", "lat": 31.2304, "lon": 121.4737, "market_keyword": "Shanghai"},
    {"name": "Beijing", "country": "CN", "lat": 39.9042, "lon": 116.4074, "market_keyword": "Beijing"},
    {"name": "Guangzhou", "country": "CN", "lat": 23.1291, "lon": 113.2644, "market_keyword": "Guangzhou"},
    {"name": "Seoul", "country": "KR", "lat": 37.5665, "lon": 126.9780, "market_keyword": "Seoul"},
    {"name": "Tokyo", "country": "JP", "lat": 35.6762, "lon": 139.6503, "market_keyword": "Tokyo"},
]

# --- API keys / endpoints ---
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct:free")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

APIFY_TOKEN = os.getenv("APIFY_TOKEN", "")
APIFY_WEATHER_ACTOR = os.getenv("APIFY_WEATHER_ACTOR", "oneary/weather-database-scraper")

GAMMA_API_URL = "https://gamma-api.polymarket.com"
CLOB_API_URL = "https://clob.polymarket.com"
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_ENSEMBLE_URL = "https://ensemble-api.open-meteo.com/v1/ensemble"

# --- Risk management ---
STARTING_BANKROLL = float(os.getenv("STARTING_BANKROLL", "1000"))
KELLY_FRACTION = 0.15
MIN_EDGE = 0.06
MAX_POSITION_PCT = 0.10


HEDGE_TRIGGER_PCT = 0.08

# --- Telegram Bot ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")