"""
stages/stage2_models.py
----------------------------------------------------------------
Stage 2: For each manufacturer, discover their compressor models
via web search + scraping + Gemini extraction.
Supports pgvector RAG similarity deduplication.

Output: data/output/models.json
"""

import json
from tqdm import tqdm
from sqlalchemy.orm import Session

from config import MODELS_JSON, MAX_MODELS_PER_MANUFACTURER
from utils.web_search import search
from utils.scraper import scrape_search_results, fetch_dynamic
from utils.genai_extractor import extract_models, embed_text


def _build_model_query(manufacturer: str, compressor_type: str) -> str:
    return f'{manufacturer} official {compressor_type} product models lineup specifications site:{manufacturer.lower().replace(" ","")}.com OR {manufacturer} {compressor_type} models datasheet'


def _find_product_page(manufacturer: str, website: str, compressor_type: str) -> str | None:
    """
    Try to find the direct product catalog URL for a manufacturer.
    Returns the URL string or None.
    """
    if not website:
        return None
    query = f'site:{website} {compressor_type} products compressors'
    results = search(query, max_results=5)

    # Prefer URLs with 'product', 'catalog', 'compressor' in path
    for r in results:
        url = r.get("url", "")
        lowered = url.lower()
        if any(kw in lowered for kw in ["product", "catalog", "compressor", "range"]):
            return url

    return results[0]["url"] if results else None


def run(manufacturers_data: dict, db: Session = None) -> dict:
    """
    Run Stage 2 for all manufacturers.

    Args:
        manufacturers_data: output from Stage 1
            {compressor_type: [{"name", "country", "website"}, ...]}
        db: SQLAlchemy DB Session (optional)

    Returns:
        dict: {manufacturer_name: {"compressor_type": str, "models": [...]}}
    """
    results = {}

    print("\n" + "=" * 60)
    print("  STAGE 2 -- Model Discovery")
    print("=" * 60)

    # Flatten manufacturers list for progress bar
    all_tasks = []
    for ctype, mfrs in manufacturers_data.items():
        for mfr in mfrs:
            all_tasks.append((ctype, mfr))

    for ctype, mfr in tqdm(all_tasks, desc="Manufacturers", unit="mfr"):
        mfr_name = mfr.get("name", "")
        website  = mfr.get("website", "")

        if not mfr_name:
            continue

        print(f"\n>  {mfr_name}  [{ctype}]")

        # -- Step 1: Web search for models ----------------------
        query = _build_model_query(mfr_name, ctype)
        print(f"   🔍 Searching: {query[:70]}...")
        search_results = search(query, max_results=5)

        # -- Step 2: Try to fetch manufacturer product page -----
        page_text = scrape_search_results(search_results, max_chars=5000)

        # Also try direct product page if website known
        if website and len(page_text) < 2000:
            direct_url = _find_product_page(mfr_name, website, ctype)
            if direct_url:
                print(f"   🌐 Fetching product page: {direct_url[:60]}...")
                try:
                    dynamic_text = fetch_dynamic(direct_url, max_chars=5000)
                    page_text = (page_text + "\n\n" + dynamic_text)[:8000]
                except Exception as e:
                    print(f"   [WARN] Dynamic fetch failed: {e}")

        # -- Step 3: Gemini extraction --------------------------
        models = []
        if page_text.strip():
            print(f"   🤖 Extracting models with Gemini...")
            try:
                models = extract_models(mfr_name, ctype, page_text)
            except Exception as e:
                print(f"   [WARN] Model extraction failed: {e}")

        # -- Step 4: Fallback search with model numbers ---------
        if not models:
            print(f"   🔄 Fallback: direct model search...")
            fallback_query = f"{mfr_name} {ctype} model numbers specifications datasheet"
            fallback_results = search(fallback_query, max_results=3)
            fallback_text    = scrape_search_results(fallback_results, max_chars=5000)
            try:
                models = extract_models(mfr_name, ctype, fallback_text)
            except Exception as e:
                print(f"   [ERROR] Fallback failed: {e}")

        # -- Step 5: Cap to limit -------------------------------
        models = models[:MAX_MODELS_PER_MANUFACTURER]

        # -- Step 6: DB Insertion & RAG Deduplication -----------
        if db:
            import database.crud as crud
            type_obj = crud.get_or_create_compressor_type(db, name=ctype)
            mfr_obj = crud.get_or_create_manufacturer(
                db, 
                name=mfr_name, 
                country=mfr.get("country", ""), 
                website=website
            )

            processed_models = []
            for m in models:
                model_name = m.get("model_name", "")
                series = m.get("series", "")
                product_url = m.get("product_url", "")

                if not model_name:
                    continue

                # Generate semantic text vector
                text_to_embed = f"{mfr_name} {ctype} model {model_name}"
                embedding = embed_text(text_to_embed)

                # RAG Deduplication Vector Match
                similar_model = crud.find_similar_model(
                    db,
                    type_id=type_obj.id,
                    manufacturer_id=mfr_obj.id,
                    query_embedding=embedding,
                    model_name=model_name
                )

                if similar_model:
                    print(f"      [RAG Match] '{model_name}' overlaps with existing model '{similar_model.model_name}' (De-duplicated)")
                    m["is_duplicate"] = True
                    m["model_id"] = similar_model.id
                else:
                    new_model = crud.create_compressor_model(
                        db,
                        type_id=type_obj.id,
                        subtype_id=None,
                        manufacturer_id=mfr_obj.id,
                        model_name=model_name,
                        series=series,
                        product_url=product_url,
                        embedding=embedding
                    )
                    m["is_duplicate"] = False
                    m["model_id"] = new_model.id
                
                processed_models.append(m)
            
            models = processed_models

        results[mfr_name] = {
            "compressor_type": ctype,
            "manufacturer_info": mfr,
            "models": models,
        }

        print(f"   ✅ Found {len(models)} models:")
        for m in models:
            dup_tag = " [Existing DB Hit]" if m.get("is_duplicate") else ""
            print(f"      • {m.get('model_name', '?')}  [{m.get('series', '')}]{dup_tag}")

    # -- Save output --------------------------------------------
    with open(MODELS_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    total_models = sum(len(v["models"]) for v in results.values())
    print(f"\n💾 Saved -> {MODELS_JSON}")
    print(f"   Total models found: {total_models}")

    return results
