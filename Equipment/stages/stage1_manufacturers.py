"""
stages/stage1_manufacturers.py
----------------------------------------------------------------
Stage 1: For each compressor type, discover manufacturers via
web search + scraping + Gemini extraction.
Saves manufacturers into database if SQL session is provided.

Output: data/output/manufacturers.json
"""

import json
from tqdm import tqdm
from sqlalchemy.orm import Session

from config import MANUFACTURERS_JSON, MAX_MANUFACTURERS_PER_TYPE
from utils.web_search import search
from utils.scraper import scrape_search_results
from utils.genai_extractor import extract_manufacturers, enrich_manufacturer_info


def _build_query(compressor: dict) -> str:
    """Build an effective search query for this compressor type."""
    ctype = compressor["type"]
    subtypes = compressor.get("subtypes", [])
    apps = compressor.get("applications", [])

    parts = [f'"{ctype}" manufacturers brands companies']
    if subtypes:
        parts.append(" ".join(subtypes[:2]))
    if apps:
        parts.append(apps[0])
    parts.append("top global list")

    return " ".join(parts)


def run(compressors: list[dict], db: Session = None) -> dict:
    """
    Run Stage 1 for all compressor types.

    Args:
        compressors: list of compressor dicts from data/compressors.json
        db: SQLAlchemy DB Session (optional)

    Returns:
        dict mapping compressor_type -> list of manufacturer dicts
    """
    results = {}

    print("\n" + "=" * 60)
    print("  STAGE 1 -- Manufacturer Discovery")
    print("=" * 60)

    for compressor in tqdm(compressors, desc="Compressor Types", unit="type"):
        ctype    = compressor["type"]
        subtypes = compressor.get("subtypes", [])

        print(f"\n>  {ctype}")

        # -- DB Init Category -----------------------------------
        if db:
            import database.crud as crud
            type_obj = crud.get_or_create_compressor_type(db, name=ctype)
            for subtype in subtypes:
                crud.get_or_create_compressor_subtype(db, name=subtype, type_id=type_obj.id)

        # -- Step 1: Web Search ---------------------------------
        query   = _build_query(compressor)
        print(f"   🔍 Searching: {query[:70]}...")
        results_raw = search(query, max_results=5)

        # -- Step 2: Scrape + combine text ----------------------
        print(f"   🌐 Scraping {len(results_raw)} pages...")
        combined_text = scrape_search_results(results_raw, max_chars=6000)

        # -- Step 3: Gemini extraction --------------------------
        manufacturers = []
        if combined_text.strip():
            print(f"   🤖 Extracting manufacturers with Gemini...")
            try:
                manufacturers = extract_manufacturers(ctype, subtypes, combined_text)
            except Exception as e:
                print(f"   [WARN] Gemini extraction failed: {e}")

        # -- Step 4: Fallback -- ask Gemini from knowledge -------
        if not manufacturers:
            print(f"   🤖 No results from web -- using Gemini knowledge fallback...")
            fallback_query = (
                f"List the top 15 major manufacturers of {ctype}. "
                f"Subtypes: {', '.join(subtypes) if subtypes else 'general'}"
            )
            fallback_results = search(fallback_query, max_results=3)
            fallback_text    = scrape_search_results(fallback_results, max_chars=4000)
            try:
                manufacturers = extract_manufacturers(ctype, subtypes, fallback_text)
            except Exception as e:
                print(f"   [ERROR] Fallback also failed: {e}")
                manufacturers = []

        # -- Step 5: Cap to limit -------------------------------
        manufacturers = manufacturers[:MAX_MANUFACTURERS_PER_TYPE]
        results[ctype] = manufacturers

        print(f"   ✅ Found {len(manufacturers)} manufacturers:")
        for m in manufacturers:
            print(f"      • {m.get('name', 'Unknown')} ({m.get('country', '?')}) -- {m.get('website', '')}")

        # -- DB Populate manufacturers --------------------------
        if db:
            import database.crud as crud
            for m in manufacturers:
                crud.get_or_create_manufacturer(
                    db,
                    name=m.get("name", ""),
                    country=m.get("country", ""),
                    website=m.get("website", ""),
                    description=m.get("description", "")
                )

    # -- Save output --------------------------------------------
    with open(MANUFACTURERS_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n💾 Saved -> {MANUFACTURERS_JSON}")
    print(f"   Total manufacturers: {sum(len(v) for v in results.values())}")

    return results
