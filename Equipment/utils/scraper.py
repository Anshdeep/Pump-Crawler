"""
utils/scraper.py -- Static (httpx+BS4) and dynamic (Playwright) page scrapers
Fixes:
 - Skip PDF/binary URLs before attempting fetch
 - Use 'domcontentloaded' instead of 'networkidle' (faster, less timeout)
 - Increased Playwright timeout to 45s
 - Better text cleanup
"""
import time
import httpx
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential
from config import REQUEST_DELAY_SECONDS
from utils import cache

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# File extensions to skip — can't scrape text from these
SKIP_EXTENSIONS = (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".zip", ".rar")


def _is_skippable(url: str) -> bool:
    """Return True if this URL points to a binary/document file we can't scrape."""
    return any(url.lower().split("?")[0].endswith(ext) for ext in SKIP_EXTENSIONS)


def _parse_html(html: str, max_chars: int) -> str:
    """Parse HTML, strip noise tags, return clean text."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form",
                     "noscript", "svg", "iframe"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    lines = [l.strip() for l in text.splitlines() if len(l.strip()) > 2]
    return "\n".join(lines)[:max_chars]


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_static(url: str, max_chars: int = 8000) -> str:
    """
    Fetch a static page and return cleaned text (up to max_chars).
    Uses cache to avoid re-fetching. Skips binary/PDF URLs.
    """
    if _is_skippable(url):
        return ""

    cache_key = f"static::{url}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    time.sleep(REQUEST_DELAY_SECONDS)

    response = httpx.get(url, headers=HEADERS, timeout=20, follow_redirects=True)
    response.raise_for_status()

    # Skip if response is not HTML
    content_type = response.headers.get("content-type", "")
    if "text/html" not in content_type and "text/plain" not in content_type:
        return ""

    text = _parse_html(response.text, max_chars)
    cache.set(cache_key, text)
    return text


def fetch_dynamic(url: str, max_chars: int = 8000) -> str:
    """
    Fetch a JS-rendered page using Playwright (headless Chromium).
    Falls back to static fetch if Playwright is unavailable or times out.
    Skips PDF/binary URLs entirely.
    """
    if _is_skippable(url):
        return ""

    cache_key = f"dynamic::{url}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(extra_http_headers=HEADERS)
            page = context.new_page()

            # Use domcontentloaded (faster) and longer timeout
            response = page.goto(url, timeout=45000, wait_until="domcontentloaded")

            # Skip non-HTML responses (PDFs etc. trigger downloads)
            if response and "text/html" not in response.headers.get("content-type", ""):
                browser.close()
                return ""

            time.sleep(1)  # let lazy content settle
            html = page.content()
            browser.close()

        text = _parse_html(html, max_chars)
        cache.set(cache_key, text)
        return text

    except Exception as e:
        err = str(e)
        if "Download is starting" in err or "ERR_ABORTED" in err:
            return ""  # PDF/download — skip silently
        print(f"  [WARN] Playwright failed ({err[:80]}), falling back to static fetch")
        return fetch_static(url, max_chars)


def scrape_search_results(results: list[dict], max_chars: int = 6000) -> str:
    """
    Combine content from a list of search result dicts.
    Uses search snippets first, then tries static fetch on URLs.
    """
    combined = []
    total = 0

    for r in results:
        snippet = r.get("content", "").strip()
        if snippet:
            combined.append(snippet)
            total += len(snippet)

        url = r.get("url", "")
        if total < max_chars and url and not _is_skippable(url):
            try:
                page_text = fetch_static(url, max_chars=3000)
                if page_text:
                    combined.append(page_text)
                    total += len(page_text)
            except Exception:
                pass  # skip unreachable URLs

        if total >= max_chars:
            break

    return "\n\n---\n\n".join(combined)[:max_chars]
