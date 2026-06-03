"""
stages/stage1_manufacturers.py
----------------------------------------------------------------
Stage 1: For each Equipment type, discover manufacturers via
web search + scraping + Gemini extraction.
Saves manufacturers into database if SQL session is provided.

Output: data/output/manufacturers.json
"""

import json
from tqdm import tqdm
from sqlalchemy.orm import Session

import config
from utils.web_search import search
from utils.scraper import scrape_search_results
from utils.genai_extractor import extract_manufacturers, enrich_manufacturer_info



def _build_query(equipment: dict, master_name: str = "equipment") -> str:
    """Build an effective search query for this equipment type."""
    ctype = equipment["type"]
    subtypes = equipment.get("subtypes", [])
    apps = equipment.get("applications", [])
    part_item = "It is required to search leading manufacturers of industrial grade " + equipment["type"]

    # If ctype doesn't end with master_name, append plural master_name to query for precision
    kw_suffix = ""
    master_lower = master_name.lower()
    if not any(kw in ctype.lower() for kw in [master_lower, master_lower + "s"]):
        kw_suffix = f" {master_lower}s" if not master_lower.endswith("s") else f" {master_lower}"

    parts = []
    parts.append(part_item)
    parts += [f'"{ctype}"{kw_suffix} manufacturers companies']
    if subtypes:
        parts.append(" ".join(subtypes[:2]))
    if apps:
        parts.append(apps[0])
    parts.append("top global list")

    return " ".join(parts)


def run(equipments: list[dict], db: Session = None, check_cancel=None) -> dict:
    """
    Run Stage 1 for all equipment types.

    Args:
        equipments: list of equipment dicts
        db: SQLAlchemy DB Session (optional)
        check_cancel: Function to check if task was cancelled (optional)

    Returns:
        dict mapping equipment_type -> list of manufacturer dicts
    """
    results = {}

    print("\n" + "=" * 60)
    print("  STAGE 1 -- Manufacturer Discovery")
    print("=" * 60)

    for equipment in tqdm(equipments, desc="Equipment Types", unit="type"):
        if check_cancel:
            check_cancel()
            
        ctype    = equipment["type"]
        subtypes = equipment.get("subtypes", [])
        master_id = equipment.get("equipment_master_id")

        if db and not master_id:
            from database.models import EquipmentType
            type_in_db = db.query(EquipmentType).filter(EquipmentType.name == ctype).first()
            if type_in_db:
                master_id = type_in_db.equipment_master_id

        # NOTE: Removed the dangerous .first() fallback that used to blindly grab whichever
        # EquipmentMaster row happened to be first in the DB (e.g. Compressor instead of Pump).
        # If master_id is still unresolved at this point, we raise a clear error instead of
        # silently crawling the wrong equipment category.
        if not master_id:
            raise ValueError(
                f"Could not resolve EquipmentMaster for equipment type '{ctype}'. "
                "Ensure the equipment dict carries 'equipment_master_id', or that the type "
                "already exists in the database with a valid equipment_master_id."
            )

        print(f"\n>  {ctype}")

        master_name = "equipment"  # Neutral fallback; overridden by DB master lookup below
        # -- DB Init Category -----------------------------------
        if db:
            import database.crud as crud
            from database.models import EquipmentMaster
            master_obj = db.query(EquipmentMaster).filter(EquipmentMaster.id == master_id).first()
            if master_obj:
                master_name = master_obj.name
                
            type_obj = crud.get_or_create_equipment_type(db, name=ctype, equipment_master_id=master_id)
            for subtype in subtypes:
                crud.get_or_create_equipment_subtype(db, name=subtype, type_id=type_obj.id)

        # -- Step 1: Web Search ---------------------------------
        query   = _build_query(equipment, master_name)
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
                manufacturers = extract_manufacturers(master_name, ctype, subtypes, combined_text)
            except Exception as e:
                print(f"   [WARN] Gemini extraction failed: {e}")

        # -- Step 4: Fallback -- ask Gemini from knowledge -------
        if not manufacturers:
            print(f"   🤖 No results from web -- using Gemini knowledge fallback...")
            
            # Ensure query includes master category keyword suffix for precision
            master_lower = master_name.lower()
            query_suffix = ""
            if not any(kw in ctype.lower() for kw in [master_lower, master_lower + "s"]):
                query_suffix = f" {master_name}"
                
            fallback_query = (
                f"List the top 15 major manufacturers of {ctype}{query_suffix}. "
                f"Subtypes: {', '.join(subtypes) if subtypes else 'general'}"
            )
            fallback_results = search(fallback_query, max_results=3)
            fallback_text    = scrape_search_results(fallback_results, max_chars=4000)
            try:
                manufacturers = extract_manufacturers(master_name, ctype, subtypes, fallback_text)
            except Exception as e:
                print(f"   [ERROR] Fallback also failed: {e}")
                manufacturers = []

        # -- Step 5: Cap to limit -------------------------------
        manufacturers = manufacturers[:config.MAX_MANUFACTURERS_PER_TYPE]
        results[ctype] = manufacturers

        print(f"   ✅ Found {len(manufacturers)} manufacturers:")
        for m in manufacturers:
            print(f"      • {m.get('name', 'Unknown')} ({m.get('country', '?')}) -- {m.get('website', '')}")

        # -- DB Populate manufacturers --------------------------
        if db:
            import database.crud as crud
            from database.models import Model
            for m in manufacturers:
                mfr_obj = crud.get_or_create_manufacturer(
                    db,
                    name=m.get("name", ""),
                    country=m.get("country", ""),
                    website=m.get("website", ""),
                    description=m.get("description", "")
                )
                # Create a placeholder model to link this manufacturer to this equipment type
                # so that they show up in the frontend directory filters before models are harvested
                existing_placeholder = db.query(Model).filter(
                    Model.manufacturer_id == mfr_obj.id,
                    Model.equipment_type_id == type_obj.id
                ).first()
                if not existing_placeholder:
                    crud.create_equipment_model(
                        db,
                        equipment_master_id=master_id,
                        equipment_type_id=type_obj.id,
                        equipment_subtype_id=None,
                        manufacturer_id=mfr_obj.id,
                        model_name="TEMP_PLACEHOLDER",
                        series="Placeholder",
                        product_url=""
                    )

    # -- Save output --------------------------------------------
    with open(config.MANUFACTURERS_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n💾 Saved -> {config.MANUFACTURERS_JSON}")
    print(f"   Total manufacturers: {sum(len(v) for v in results.values())}")

    return results
