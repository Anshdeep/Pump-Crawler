"""
utils/web_search.py -- Tavily search API wrapper with fallback to DuckDuckGo
"""
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from config import TAVILY_API_KEY
from utils import cache

TAVILY_ENDPOINT = "https://api.tavily.com/search"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def tavily_search(query: str, max_results: int = 5) -> list[dict]:
    """
    Search via Tavily API. Returns list of {url, title, content} dicts.
    """
    cache_key = f"tavily::{query}::{max_results}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    headers = {"Content-Type": "application/json"}
    payload = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "search_depth": "basic",
        "max_results": max_results,
        "include_raw_content": False,
    }

    response = httpx.post(TAVILY_ENDPOINT, json=payload, headers=headers, timeout=10)
    response.raise_for_status()
    data = response.json()

    results = [
        {
            "url":     r.get("url", ""),
            "title":   r.get("title", ""),
            "content": r.get("content", ""),
        }
        for r in data.get("results", [])
    ]

    cache.set(cache_key, results)
    return results


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def duckduckgo_search(query: str, max_results: int = 5) -> list[dict]:
    """
    Fallback: DuckDuckGo Lite HTML scrape (no API key needed).
    """
    from bs4 import BeautifulSoup

    cache_key = f"ddg::{query}::{max_results}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    url = "https://html.duckduckgo.com/html/"
    params = {"q": query}
    headers = {"User-Agent": "Mozilla/5.0 (compatible; EquipmentCrawlerBot/1.0)"}

    response = httpx.post(url, data=params, headers=headers, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")
    results = []
    for a in soup.select(".result__a")[:max_results]:
        results.append({
            "url":     a.get("href", ""),
            "title":   a.get_text(strip=True),
            "content": "",
        })

    cache.set(cache_key, results)
    return results


def search(query: str, max_results: int = 5) -> list[dict]:

    print("########### Tavily Query ########### ",query)
    """
    Unified search: tries Tavily first, falls back to DuckDuckGo.
    """
    if TAVILY_API_KEY:
        try:
            return tavily_search(query, max_results)
        except Exception as e:
            print(f"  [WARN] Tavily failed ({e}), falling back to DuckDuckGo")
    return duckduckgo_search(query, max_results)
