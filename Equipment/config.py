"""
config.py -- Central configuration loaded from .env
"""
import os
from dotenv import load_dotenv

load_dotenv()

# -- API Keys ---------------------------------------------------------------
GEMINI_API_KEY   = os.getenv("GEMINI_API_KEY", "")
TAVILY_API_KEY   = os.getenv("TAVILY_API_KEY", "")

# -- Crawler Limits ---------------------------------------------------------
MAX_MANUFACTURERS_PER_TYPE    = int(os.getenv("MAX_MANUFACTURERS_PER_TYPE", 3))
MAX_MODELS_PER_MANUFACTURER   = int(os.getenv("MAX_MODELS_PER_MANUFACTURER", 5))
REQUEST_DELAY_SECONDS         = float(os.getenv("REQUEST_DELAY_SECONDS", 1.5))
CACHE_ENABLED                 = os.getenv("CACHE_ENABLED", "true").lower() == "true"

# -- Paths ------------------------------------------------------------------
BASE_DIR          = os.path.dirname(os.path.abspath(__file__))
DATA_DIR          = os.path.join(BASE_DIR, "data")
OUTPUT_DIR        = os.path.join(DATA_DIR, "output")
CACHE_DIR         = os.path.join(DATA_DIR, "cache")

# -- Input ------------------------------------------------------------------
# Equipment types are seeded dynamically from JSON files in DATA_DIR at startup
# (see database/connection.py init_db). Add a new <master>.json to DATA_DIR to
# introduce a new equipment master category (e.g. pumps.json, valves.json).

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(CACHE_DIR,  exist_ok=True)

# -- Output Files -----------------------------------------------------------
MANUFACTURERS_JSON  = os.path.join(OUTPUT_DIR, "manufacturers.json")
MODELS_JSON         = os.path.join(OUTPUT_DIR, "models.json")
FINAL_OUTPUT_JSON   = os.path.join(OUTPUT_DIR, "equipment_data.json")

# -- Gemini Model -----------------------------------------------------------
GEMINI_MODEL = "gemini-3.1-flash-lite"
