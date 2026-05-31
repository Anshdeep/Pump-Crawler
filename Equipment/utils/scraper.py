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


def _dismiss_popups(page):
    """Attempt to click through and remove overlays, cookies banners, region blocks, and popups."""
    import time
    
    # 1. Search for common consent, location selection, and close buttons
    try:
        selectors = [
            # Cookie consents
            "button:has-text('accept')", "button:has-text('allow')", "button:has-text('agree')",
            "button:has-text('accept all')", "button:has-text('allow all')", "button:has-text('consent')",
            "a:has-text('accept')", "a:has-text('agree')", "button:has-text('OK')", "button:has-text('Ok')",
            # Region, Location & Language selection gates (e.g. Ingersoll Rand type modals)
            "button:has-text('United States')", "a:has-text('United States')", "button:has-text('English')",
            "a:has-text('English')", "button:has-text('Global')", "a:has-text('Global')",
            "button:has-text('US')", "button:has-text('continue')", "a:has-text('continue')",
            "button:has-text('select location')", "button:has-text('go to site')", "a:has-text('go to site')",
            # General close modals
            "button:has-text('close')", "button:has-text('dismiss')", "[aria-label*='close']",
            "[class*='close']", "button:has-text('×')", "span:has-text('×')"
        ]
        
        for selector in selectors:
            elements = page.locator(selector)
            try:
                count = elements.count()
                for i in range(count):
                    el = elements.nth(i)
                    if el.is_visible() and el.is_enabled():
                        # Click the button to bypass the region block or popup
                        el.click(timeout=1500)
                        print(f"      [Playwright] Clicked popup bypass element: {selector}")
                        time.sleep(0.5)
                        break
            except Exception:
                continue
    except Exception:
        pass
        
    # 2. Run an aggressive client-side DOM cleanser to remove overlays and unlock scrolling
    try:
        page.evaluate("""() => {
            try {
                const badSelectors = [
                    "[class*='cookie']", "[class*='consent']", "[class*='banner']", "[class*='popup']", 
                    "[class*='modal']", "[class*='overlay']", "[class*='backdrop']", "[class*='gate']", 
                    "[class*='region']", "[class*='location']", "[class*='language']", "[class*='selector']",
                    "[id*='cookie']", "[id*='consent']", "[id*='banner']", "[id*='popup']", 
                    "[id*='modal']", "[id*='overlay']", "[id*='backdrop']", "[id*='gate']", 
                    "[id*='region']", "[id*='location']", "[id*='language']", "[id*='selector']",
                    ".modal", ".backdrop", ".overlay", ".cookie", ".consent", ".privacy",
                    "#cookie", "#consent", "#privacy", "#overlay", "#backdrop", ".modal-backdrop"
                ];

                const cleanDOM = () => {
                    // Remove generic popups, overlays, backdrop elements
                    badSelectors.forEach(sel => {
                        try {
                            document.querySelectorAll(sel).forEach(el => {
                                // Don't accidentally wipe out main content wrappers
                                if (el.tagName !== 'BODY' && el.tagName !== 'HTML' && el.tagName !== 'MAIN') {
                                    el.remove();
                                }
                            });
                        } catch(e) {}
                    });

                    // Find and delete high-z-index absolute/fixed overlays covering screen
                    const allElements = document.getElementsByTagName('*');
                    for (let el of allElements) {
                        try {
                            const style = window.getComputedStyle(el);
                            const zIndex = parseInt(style.zIndex);
                            const position = style.position;
                            
                            if ((position === 'fixed' || position === 'absolute') && zIndex >= 100) {
                                const className = (el.className || '').toString().toLowerCase();
                                const elementId = (el.id || '').toString().toLowerCase();
                                // Keep main page components like standard navigation or headers
                                if (!className.includes('nav') && !className.includes('header') &&
                                    !elementId.includes('nav') && !elementId.includes('header') &&
                                    el.tagName !== 'HEADER' && el.tagName !== 'NAV') {
                                    el.remove();
                                }
                            }
                        } catch(e) {}
                    }

                    // Unlock body & HTML elements' locked scrolling properties
                    const unlockElement = (el) => {
                        if (!el) return;
                        el.style.setProperty('overflow', 'visible', 'important');
                        el.style.setProperty('overflow-y', 'visible', 'important');
                        el.style.setProperty('position', 'static', 'important');
                        el.style.setProperty('height', 'auto', 'important');
                        el.style.setProperty('max-height', 'none', 'important');
                        
                        // Strip typical modal locks
                        const lockClasses = ['modal-open', 'no-scroll', 'overflow-hidden', 'scroll-lock', 'cookie-active'];
                        lockClasses.forEach(c => el.classList.remove(c));
                    };
                    unlockElement(document.body);
                    unlockElement(document.documentElement);
                };

                // Execute immediate cleanup
                cleanDOM();

                // Setup persistent MutationObserver if not already created
                if (!window._domCleanserObserver) {
                    const observer = new MutationObserver(() => {
                        try {
                            cleanDOM();
                        } catch(e) {}
                    });
                    observer.observe(document.documentElement, { childList: true, subtree: true });
                    window._domCleanserObserver = observer;
                }
            } catch(e) {}
        }""")
    except Exception as e:
        print(f"      [Playwright Code Injection Error] {e}")

    # 3. Inject standard fallback CSS just in case
    try:
        css_to_inject = """
        [class*='cookie'], [class*='consent'], [class*='banner'], [class*='popup'], [class*='modal'],
        [id*='cookie'], [id*='consent'], [id*='banner'], [id*='popup'], [id*='modal'],
        .overlay, .backdrop, #overlay, #backdrop, .modal-backdrop {
            display: none !important;
            pointer-events: none !important;
            opacity: 0 !important;
            visibility: hidden !important;
        }
        body, html {
            overflow: auto !important;
            position: static !important;
        }
        """
        page.add_style_tag(content=css_to_inject)
    except Exception:
        pass


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

            # Phase 1: Wait for domcontentloaded (very fast)
            response = page.goto(url, timeout=45000, wait_until="domcontentloaded")

            # Skip non-HTML responses (PDFs etc. trigger downloads)
            if response and "text/html" not in response.headers.get("content-type", ""):
                browser.close()
                return ""

            # Try waiting for the full load state with a short timeout to let initial assets render
            try:
                page.wait_for_load_state("load", timeout=5000)
            except Exception:
                pass

            # First dismissal pass (captures immediate cookie and overlay barriers)
            _dismiss_popups(page)

            # Settle period: sleep to allow slow lazy-loaded overlays (like region selectors) to mount
            time.sleep(2.0)

            # Second dismissal pass (captures asynchronously loaded dialogs)
            _dismiss_popups(page)

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
