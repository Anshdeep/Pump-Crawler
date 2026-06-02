"""
stages/stage3_attributes.py
----------------------------------------------------------------
Stage 3: For each model, fetch its product page and extract
technical attributes using Gemini.
Supports loading cached specs directly from the database to avoid search/crawls.

Output: data/output/compressors_data.json
"""

import json
from tqdm import tqdm
from sqlalchemy.orm import Session

import config
from utils.scraper import fetch_dynamic, fetch_static, scrape_search_results, filter_technical_specs_only
from utils.genai_extractor import extract_attributes
from utils.web_search import search


def _fetch_model_page(model: dict, manufacturer: str, compressor_type: str, master_name: str = "compressor") -> str:
    """
    Attempt to fetch the product page for this model.
    Priority: product_url -> web search for spec sheet.
    """
    product_url = (model.get("product_url") or "").strip()

    # Try the direct URL first
    if product_url and product_url.startswith("http"):
        try:
            return fetch_dynamic(product_url, max_chars=8000)
        except Exception:
            pass  # fall through to search

    # Fallback: search for model specs
    model_name = model.get("model_name", "")
    
    # Try a broader, highly flexible search query
    kw_suffix = ""
    master_lower = master_name.lower()
    if not any(kw in compressor_type.lower() for kw in [master_lower, master_lower + "s"]):
        kw_suffix = f" {master_lower}"

    query = f'{manufacturer} {model_name} {compressor_type}{kw_suffix} specifications datasheet technical'
    results = search(query, max_results=4)

    if not results:
        # Strict backup query
        strict_query = f'"{manufacturer}" "{model_name}" specifications'
        results = search(strict_query, max_results=3)

    if results:
        # Try fetching the first 2 candidate pages in sequence (fast limit to avoid sequential chromium loads)
        for r in results[:2]:
            url = r.get("url", "")
            if url:
                try:
                    text = fetch_dynamic(url, max_chars=8000)
                    # Lower content threshold to 100 characters so small spec grids are not skipped
                    if text and len(text.strip()) > 100:
                        print(f"      [Harvester Specs] Successfully retrieved page content ({len(text)} chars) from {url[:60]}")
                        return text
                    else:
                        print(f"      [Harvester Specs] Content from {url[:50]} too short ({len(text) if text else 0} chars), skipping...")
                except Exception as e:
                    continue

    # Last resort: use search snippet text
    return scrape_search_results(results, max_chars=5000)


# In-memory shared page URL and series content cache
URL_CONTENT_CACHE = {}

def _fetch_model_page_cached(model: dict, manufacturer: str, compressor_type: str, master_name: str = "compressor") -> str:
    """
    Wrapper around _fetch_model_page using in-memory cache to reuse crawled 
    pages across models belonging to the same product series.
    """
    product_url = (model.get("product_url") or "").strip()
    series = (model.get("series") or "").strip()
    
    # 1. Try to reuse cached page content by exact direct URL
    if product_url and product_url in URL_CONTENT_CACHE:
        print(f"      [Cache Hit] Reusing catalog text by URL: {product_url[:65]}...")
        return URL_CONTENT_CACHE[product_url]
        
    # 2. Try to reuse by Series family (if another model in this series already crawled it)
    series_key = f"{manufacturer}::{series}"
    if series and series_key in URL_CONTENT_CACHE:
        print(f"      [Cache Hit] Reusing catalog text for Series: '{series}' (Crawling avoided!)")
        return URL_CONTENT_CACHE[series_key]
        
    # Settle fresh crawl
    text = _fetch_model_page(model, manufacturer, compressor_type, master_name)
    
    # Cache content for subsequent models to reuse
    if text and len(text.strip()) > 300:
        if product_url:
            URL_CONTENT_CACHE[product_url] = text
        if series:
            URL_CONTENT_CACHE[series_key] = text
            
    return text


def run(models_data: dict, db: Session = None, check_cancel=None) -> list[dict]:
    """
    Run Stage 3 for all models.

    Args:
        models_data: output from Stage 2
            {manufacturer_name: {"compressor_type": str, "models": [...]}}
        db: SQLAlchemy DB Session (optional)
        check_cancel: Function to check if task was cancelled (optional)

    Returns:
        list of flat compressor records with full attributes
    """
    final_records = []

    print("\n" + "=" * 60)
    print("  STAGE 3 -- Attribute Extraction")
    print("=" * 60)

    # Build flat task list
    all_tasks = []
    for mfr_name, mfr_data in models_data.items():
        ctype    = mfr_data.get("compressor_type", "")
        mfr_info = mfr_data.get("manufacturer_info", {})
        for model in mfr_data.get("models", []):
            all_tasks.append((ctype, mfr_name, mfr_info, model))

    for ctype, mfr_name, mfr_info, model in tqdm(all_tasks, desc="Models", unit="model"):
        if check_cancel:
            check_cancel()
            
        model_name  = model.get("model_name", "Unknown")
        series      = model.get("series", "")
        product_url = model.get("product_url", "")
        model_id    = model.get("model_id")

        print(f"\n>  {mfr_name} -- {model_name}")

        # Resolve parent master category name from DB
        master_name = "compressor"
        if db and model_id:
            from database.models import Model
            model_obj = db.query(Model).filter(Model.id == model_id).first()
            if model_obj and model_obj.equipment_master:
                master_name = model_obj.equipment_master.name

        # -- DB Spec Lookup -------------------------------------
        db_attributes = None
        if db and model_id:
            from database.models import TechnicalAttribute, Model as ModelTable
            db_attr_record = db.query(TechnicalAttribute).filter(TechnicalAttribute.model_id == model_id).first()
            if db_attr_record and db_attr_record.attributes:
                db_attributes = db_attr_record.attributes
                print(f"   [RAG Hit] Loaded existing specs from DB for '{model_name}' (Crawling avoided!)")
                model_obj = db.query(ModelTable).filter(ModelTable.id == model_id).first()
                if model_obj and not model_obj.is_harvested:
                    model_obj.is_harvested = True
                    db.commit()

        # -- Fetch & extract if not cached in DB ----------------
        attributes = {}
        if db_attributes:
            attributes = db_attributes
        else:
            # -- Step 1: Fetch page ---------------------------------
            print(f"   🌐 Fetching product page...")
            try:
                page_text = _fetch_model_page_cached(model, mfr_name, ctype, master_name)
            except Exception as e:
                print(f"   [WARN] Could not fetch page: {e}")
                page_text = ""

            # -- Step 2: Gemini attribute extraction ----------------
            if page_text and page_text.strip():
                # Apply high-density regex pre-filtering to slash token consumption
                filtered_text = filter_technical_specs_only(page_text)
                print(f"      [Specs Optimizer] Reduced input text from {len(page_text)} to {len(filtered_text)} characters!")
                
                if filtered_text.strip():
                    print(f"   🤖 Extracting attributes with Gemini...")
                    try:
                        type_context = f"{ctype} {master_name.lower()}" if master_name.lower() not in ctype.lower() else ctype
                        attributes = extract_attributes(mfr_name, model_name, type_context, filtered_text)
                        
                        # Save to DB
                        if db and model_id and attributes:
                            import database.crud as crud
                            crud.save_technical_attributes(db, model_id, attributes)
                            from database.models import Model
                            model_obj = db.query(Model).filter(Model.id == model_id).first()
                            if model_obj:
                                model_obj.is_harvested = True
                                db.commit()
                    except Exception as e:
                        print(f"   [WARN] Attribute extraction failed: {e}")
                else:
                    print(f"   [WARN] Filtering left empty specs sheet -- attributes will be empty")
            else:
                print(f"   [WARN] No page text -- attributes will be empty")

        # -- Step 3: Assemble final record ----------------------
        record = {
            "compressor_type":    ctype,
            "manufacturer":       mfr_name,
            "manufacturer_info":  mfr_info,
            "model":              model_name,
            "series":             series,
            "product_url":        product_url,
            "attributes":         attributes,
        }
        final_records.append(record)

        # Preview a few attributes
        if attributes:
            preview = {k: v for k, v in list(attributes.items())[:4] if v is not None}
            print(f"   ✅ Attributes extracted: {len(attributes)} fields")
            print(f"      Sample: {preview}")
        else:
            print(f"   (!)️  No attributes extracted")

    # -- Save final output --------------------------------------
    with open(config.FINAL_OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(final_records, f, ensure_ascii=False, indent=2)

    print(f"\n💾 Saved -> {config.FINAL_OUTPUT_JSON}")
    print(f"   Total records: {len(final_records)}")
    print(f"   Records with attributes: {sum(1 for r in final_records if r['attributes'])}")

    return final_records
