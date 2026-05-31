import sys, os
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()

print("=== Testing Gemini API ===")
try:
    from google import genai
    from google.genai import types
    from config import GEMINI_MODEL
    api_key = os.getenv("GEMINI_API_KEY", "")
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents="Say exactly: GEMINI_OK",
        config=types.GenerateContentConfig(temperature=0.1, max_output_tokens=500)
    )
    print(f"  Gemini response: {response.text.strip()}")
    print(f"  Gemini model   : {GEMINI_MODEL}")
    print("  Gemini: CONNECTED OK")
except Exception as e:
    print(f"  Gemini ERROR: {e}")

print("")
print("=== Testing Tavily API ===")
try:
    from tavily import TavilyClient
    tvly_key = os.getenv("TAVILY_API_KEY", "")
    tc = TavilyClient(api_key=tvly_key)
    res = tc.search("air compressor manufacturers", max_results=1)
    count = len(res["results"])
    print(f"  Tavily response: {count} result(s)")
    print("  Tavily: CONNECTED OK")
except Exception as e:
    print(f"  Tavily ERROR: {e}")

print("")
print("=== Testing Scraper ===")
try:
    from utils.scraper import fetch_static
    text = fetch_static("https://httpbin.org/get", max_chars=200)
    print(f"  Fetched {len(text)} chars")
    print("  Scraper: OK")
except Exception as e:
    print(f"  Scraper ERROR: {e}")
