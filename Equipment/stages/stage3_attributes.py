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

from config import FINAL_OUTPUT_JSON
from utils.scraper import fetch_dynamic, fetch_static
from utils.genai_extractor import extract_attributes
from utils.web_search import search
from utils.scraper import scrape_search_results


def _fetch_model_page(model: dict, manufacturer: str, compressor_type: str) -> str:
    """
    Attempt to fetch the product page for this model.
    Priority: product_url -> web search for spec sheet.
    """
    product_url = model.get("product_url", "").strip()

    # Try the direct URL first
    if product_url and product_url.startswith("http"):
        try:
            return fetch_dynamic(product_url, max_chars=8000)
        except Exception:
            pass  # fall through to search

    # Fallback: search for model specs
    model_name = model.get("model_name", "")
    query = f'"{manufacturer}" "{model_name}" specifications datasheet technical'
    results = search(query, max_results=3)

    if results:
        # Try fetching the first result page
        for r in results:
            url = r.get("url", "")
            if url:
                try:
                    return fetch_dynamic(url, max_chars=8000)
                except Exception:
                    continue

    # Last resort: use search snippet text
    return scrape_search_results(results, max_chars=5000)


def run(models_data: dict, db: Session = None) -> list[dict]:
    """
    Run Stage 3 for all models.

    Args:
        models_data: output from Stage 2
            {manufacturer_name: {"compressor_type": str, "models": [...]}}
        db: SQLAlchemy DB Session (optional)

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
        model_name  = model.get("model_name", "Unknown")
        series      = model.get("series", "")
        product_url = model.get("product_url", "")
        model_id    = model.get("model_id")

        print(f"\n>  {mfr_name} -- {model_name}")

        # -- DB Spec Lookup -------------------------------------
        db_attributes = None
        if db and model_id:
            from database.models import TechnicalAttribute
            db_attr_record = db.query(TechnicalAttribute).filter(TechnicalAttribute.model_id == model_id).first()
            if db_attr_record and db_attr_record.attributes:
                db_attributes = db_attr_record.attributes
                print(f"   [RAG Hit] Loaded existing specs from DB for '{model_name}' (Crawling avoided!)")

        # -- Fetch & extract if not cached in DB ----------------
        attributes = {}
        if db_attributes:
            attributes = db_attributes
        else:
            # -- Step 1: Fetch page ---------------------------------
            print(f"   🌐 Fetching product page...")
            try:
                page_text = _fetch_model_page(model, mfr_name, ctype)
            except Exception as e:
                print(f"   [WARN] Could not fetch page: {e}")
                page_text = ""

            # -- Step 2: Gemini attribute extraction ----------------
            if page_text.strip():
                print(f"   🤖 Extracting attributes with Gemini...")
                try:
                    attributes = extract_attributes(mfr_name, model_name, ctype, page_text)
                    
                    # Save to DB
                    if db and model_id and attributes:
                        import database.crud as crud
                        crud.save_technical_attributes(db, model_id, attributes)
                except Exception as e:
                    print(f"   [WARN] Attribute extraction failed: {e}")
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
    with open(FINAL_OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(final_records, f, ensure_ascii=False, indent=2)

    print(f"\n💾 Saved -> {FINAL_OUTPUT_JSON}")
    print(f"   Total records: {len(final_records)}")
    print(f"   Records with attributes: {sum(1 for r in final_records if r['attributes'])}")

    return final_records
