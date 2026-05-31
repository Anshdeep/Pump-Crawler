"""
main.py -- Compressor Data Crawler & API Server
Orchestrates all 3 pipeline stages:
  Stage 1: Manufacturer Discovery
  Stage 2: Model Discovery
  Stage 3: Attribute Extraction

Usage (CLI):
  python main.py                    # Run full pipeline via CLI
  python main.py --stage 1          # Run only Stage 1
  python main.py --type "Air"       # Filter to specific types

Usage (API Server):
  python main.py --server           # Start FastAPI web server on port 8000
"""
import os
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
import json
import argparse
import time
from datetime import datetime

from config import (
    GEMINI_API_KEY, TAVILY_API_KEY,
    MANUFACTURERS_JSON, MODELS_JSON, FINAL_OUTPUT_JSON,
    CACHE_ENABLED, COMPRESSORS_JSON,
)
import stages.stage1_manufacturers as stage1
import stages.stage2_models        as stage2
import stages.stage3_attributes    as stage3

# FastAPI Imports
from fastapi import FastAPI, Depends, BackgroundTasks, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import database.connection as connection
import database.crud as crud
from database.models import Model, CompressorType, Manufacturer, TechnicalAttribute, CrawlHistory


# ── FastAPI App Configuration ──────────────────────────────────────────────

app = FastAPI(
    title="Compressor Crawler API",
    description="Backend API serving structured compressor technical specs with RAG deduplication",
    version="2.0.0"
)

# Enable CORS for Vue 3 frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify Vuetify client origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global crawl progress tracking state
CRAWL_PROGRESS = {
    "active": False,
    "compressor_type": None,
    "stage": "idle",
    "percent": 0,
    "status_msg": "System idle",
    "started_at": None,
    "completed_at": None,
    "discovered_manufacturers": 0,
    "discovered_models": 0,
    "enriched_records": 0,
}


def _update_progress(stage: str, percent: int, msg: str, **kwargs):
    global CRAWL_PROGRESS
    CRAWL_PROGRESS["stage"] = stage
    CRAWL_PROGRESS["percent"] = percent
    CRAWL_PROGRESS["status_msg"] = msg
    for k, v in kwargs.items():
        CRAWL_PROGRESS[k] = v


def run_crawling_background(compressor_type: str | None, no_cache: bool):
    """Orchestrate background crawling task saving straight to Postgres."""
    global CRAWL_PROGRESS
    CRAWL_PROGRESS["active"] = True
    CRAWL_PROGRESS["compressor_type"] = compressor_type or "All Categories"
    CRAWL_PROGRESS["started_at"] = datetime.now().isoformat()
    CRAWL_PROGRESS["completed_at"] = None
    
    # Force disable cache if requested
    if no_cache:
        import config
        config.CACHE_ENABLED = False
        
    db = next(connection.get_db())
    
    # Create CrawlHistory record and get initial counts
    from database.models import CrawlHistory
    from datetime import datetime as dt
    
    history_record = CrawlHistory(
        started_at=dt.now(),
        status="active",
        compressor_type=CRAWL_PROGRESS["compressor_type"],
        log_message="Crawler background task started."
    )
    db.add(history_record)
    db.commit()
    db.refresh(history_record)
    
    initial_mfrs = db.query(Manufacturer).count()
    initial_models = db.query(Model).count()
    
    try:
        # Load compressor types
        compressors = load_compressors(None)
        if compressor_type:
            compressors = filter_compressors(compressors, [compressor_type])
            
        if not compressors:
            raise ValueError(f"No compressor types matched filter: {compressor_type}")
            
        # ── Stage 1 ──
        _update_progress("Stage 1: Manufacturers", 15, f"Discovering manufacturers for {[c['type'] for c in compressors]}")
        mfrs_data = stage1.run(compressors, db=db)
        total_mfrs = sum(len(v) for v in mfrs_data.values())
        _update_progress("Stage 1 Completed", 35, f"Discovered {total_mfrs} manufacturers", discovered_manufacturers=total_mfrs)
        time.sleep(2)
        
        # ── Stage 2 ──
        _update_progress("Stage 2: Models", 45, "Discovering models & executing pgvector RAG deduplication")
        models_data = stage2.run(mfrs_data, db=db)
        total_models = sum(len(v["models"]) for v in models_data.values())
        _update_progress("Stage 2 Completed", 70, f"Discovered {total_models} models and calculated embeddings", discovered_models=total_models)
        time.sleep(2)
        
        # ── Stage 3 ──
        _update_progress("Stage 3: Attributes", 75, f"Extracting engineering attributes for {total_models} models")
        final_records = stage3.run(models_data, db=db)
        with_attrs = sum(1 for r in final_records if r.get("attributes"))
        
        # Complete
        CRAWL_PROGRESS["completed_at"] = datetime.now().isoformat()
        _update_progress(
            "Completed", 
            100, 
            f"Successfully compiled {with_attrs}/{total_models} specification attributes!",
            enriched_records=with_attrs
        )
        
        # Calculate discovered telemetry metrics
        final_mfrs = db.query(Manufacturer).count()
        final_models = db.query(Model).count()
        
        history_record.status = "completed"
        history_record.completed_at = dt.now()
        history_record.new_manufacturers_count = max(0, final_mfrs - initial_mfrs)
        history_record.new_models_count = max(0, final_models - initial_models)
        history_record.total_specs_enriched = with_attrs
        history_record.log_message = f"Crawl compiled successfully. Discovered {history_record.new_manufacturers_count} manufacturers and {history_record.new_models_count} models."
        db.commit()
        
    except Exception as e:
        print(f"[BG Crawl Error] {e}")
        _update_progress("Failed", 0, f"Error occurred: {str(e)}")
        
        history_record.status = "failed"
        history_record.completed_at = dt.now()
        history_record.log_message = f"Error: {str(e)}"
        db.commit()
        
    finally:
        CRAWL_PROGRESS["active"] = False
        db.close()


def run_brand_discovery_background(compressor_type: str | None, no_cache: bool):
    """Stage 1 ONLY: Discover manufacturers/brands for a type, and set is_approved = False."""
    global CRAWL_PROGRESS
    CRAWL_PROGRESS["active"] = True
    CRAWL_PROGRESS["compressor_type"] = compressor_type or "All Categories"
    CRAWL_PROGRESS["started_at"] = datetime.now().isoformat()
    CRAWL_PROGRESS["completed_at"] = None
    CRAWL_PROGRESS["discovered_manufacturers"] = 0
    CRAWL_PROGRESS["discovered_models"] = 0
    CRAWL_PROGRESS["enriched_records"] = 0
    
    if no_cache:
        import config
        config.CACHE_ENABLED = False
        
    db = next(connection.get_db())
    
    from database.models import CrawlHistory
    from datetime import datetime as dt
    
    history_record = CrawlHistory(
        started_at=dt.now(),
        status="active",
        compressor_type=CRAWL_PROGRESS["compressor_type"],
        log_message="Brand discovery background task started (Stage 1)."
    )
    db.add(history_record)
    db.commit()
    db.refresh(history_record)
    
    initial_mfrs = db.query(Manufacturer).count()
    
    try:
        compressors = load_compressors(None)
        if compressor_type:
            compressors = filter_compressors(compressors, [compressor_type])
            
        if not compressors:
            raise ValueError(f"No compressor types matched filter: {compressor_type}")
            
        # ── Stage 1 ──
        _update_progress("Stage 1: Manufacturers", 50, f"Discovering manufacturers for {[c['type'] for c in compressors]}")
        mfrs_data = stage1.run(compressors, db=db)
        total_mfrs = sum(len(v) for v in mfrs_data.values())
        
        CRAWL_PROGRESS["completed_at"] = datetime.now().isoformat()
        _update_progress(
            "Completed", 
            100, 
            f"Successfully extracted {total_mfrs} brands for approval workflow!",
            discovered_manufacturers=total_mfrs
        )
        
        final_mfrs = db.query(Manufacturer).count()
        
        history_record.status = "completed"
        history_record.completed_at = dt.now()
        history_record.new_manufacturers_count = max(0, final_mfrs - initial_mfrs)
        history_record.log_message = f"Brand discovery compiled successfully. Discovered {history_record.new_manufacturers_count} new brands."
        db.commit()
        
    except Exception as e:
        print(f"[BG Brand Discovery Error] {e}")
        _update_progress("Failed", 0, f"Error occurred: {str(e)}")
        
        history_record.status = "failed"
        history_record.completed_at = dt.now()
        history_record.log_message = f"Error: {str(e)}"
        db.commit()
        
    finally:
        CRAWL_PROGRESS["active"] = False
        db.close()


def run_specs_harvester_background(no_cache: bool):
    """Stage 2 and 3: For approved manufacturers only, discover models and extract specs."""
    global CRAWL_PROGRESS
    CRAWL_PROGRESS["active"] = True
    CRAWL_PROGRESS["compressor_type"] = "Approved Brands"
    CRAWL_PROGRESS["started_at"] = datetime.now().isoformat()
    CRAWL_PROGRESS["completed_at"] = None
    CRAWL_PROGRESS["discovered_manufacturers"] = 0
    CRAWL_PROGRESS["discovered_models"] = 0
    CRAWL_PROGRESS["enriched_records"] = 0
    
    if no_cache:
        import config
        config.CACHE_ENABLED = False
        
    db = next(connection.get_db())
    
    from database.models import CrawlHistory
    from datetime import datetime as dt
    
    history_record = CrawlHistory(
        started_at=dt.now(),
        status="active",
        compressor_type="Approved Brands",
        log_message="Approved specifications harvester background task started (Stages 2 & 3)."
    )
    db.add(history_record)
    db.commit()
    db.refresh(history_record)
    
    initial_models = db.query(Model).count()
    
    try:
        # Load manufacturers.json Stage 1 output file
        print("[BG Harvester] Loading manufacturers catalog...")
        try:
            manufacturers_data = load_json(MANUFACTURERS_JSON)
        except FileNotFoundError:
            # Fallback: if manufacturers.json is missing, reconstruct it from approved DB brands
            manufacturers_data = {}
            # Fetch all active compressor types in system
            types_objs = db.query(CompressorType).all()
            approved_objs = db.query(Manufacturer).filter(Manufacturer.is_approved == True).all()
            for t in types_objs:
                manufacturers_data[t.name] = [
                    {"name": m.name, "country": m.country, "website": m.website, "description": m.description}
                    for m in approved_objs
                ]
        
        # Filter: keep only approved manufacturers
        approved_objs = db.query(Manufacturer).filter(Manufacturer.is_approved == True).all()
        approved_names = {m.name.strip().lower() for m in approved_objs}
        
        filtered_data = {}
        for ctype, mfr_list in manufacturers_data.items():
            approved_list = [m for m in mfr_list if m.get("name", "").strip().lower() in approved_names]
            if approved_list:
                filtered_data[ctype] = approved_list
                
        total_approved = sum(len(v) for v in filtered_data.values())
        print(f"[BG Harvester] Filtered to {total_approved} approved brand profiles.")
        
        if not filtered_data:
            raise ValueError("No approved manufacturers found! Please approve at least one manufacturer in the Brands tab before running specifications crawler.")
            
        CRAWL_PROGRESS["discovered_manufacturers"] = total_approved
        
        # ── Stage 2 ──
        _update_progress("Stage 2: Models", 30, f"Discovering model lines for {total_approved} approved manufacturers")
        models_data = stage2.run(filtered_data, db=db)
        total_models = sum(len(v["models"]) for v in models_data.values())
        _update_progress("Stage 2 Completed", 60, f"Discovered {total_models} model records", discovered_models=total_models)
        time.sleep(2)
        
        # ── Stage 3 ──
        _update_progress("Stage 3: Attributes", 70, f"Deep technical specifications harvesting for {total_models} models")
        final_records = stage3.run(models_data, db=db)
        with_attrs = sum(1 for r in final_records if r.get("attributes"))
        
        # Complete
        CRAWL_PROGRESS["completed_at"] = datetime.now().isoformat()
        _update_progress(
            "Completed", 
            100, 
            f"Successfully enriched specifications for {with_attrs}/{total_models} active models!",
            enriched_records=with_attrs
        )
        
        final_models = db.query(Model).count()
        
        history_record.status = "completed"
        history_record.completed_at = dt.now()
        history_record.new_manufacturers_count = 0  # We harvested existing, didn't discover new brands
        history_record.new_models_count = max(0, final_models - initial_models)
        history_record.total_specs_enriched = with_attrs
        history_record.log_message = f"Harvester specs run complete. Added {history_record.new_models_count} new models and populated {with_attrs} technical sheets."
        db.commit()
        
    except Exception as e:
        print(f"[BG Harvester Error] {e}")
        _update_progress("Failed", 0, f"Error occurred: {str(e)}")
        
        history_record.status = "failed"
        history_record.completed_at = dt.now()
        history_record.log_message = f"Error: {str(e)}"
        db.commit()
        
    finally:
        CRAWL_PROGRESS["active"] = False
        db.close()


# ── FastAPI Routes ─────────────────────────────────────────────────────────

@app.post("/api/init-db", tags=["System"])
def initialize_database():
    """Enable pgvector and generate database tables."""
    try:
        connection.init_db()
        return {"status": "success", "message": "PostgreSQL 18 database with pgvector initialized!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database initialization failed: {e}")


@app.get("/api/crawl/status", tags=["Crawler"])
def get_crawl_status():
    """Retrieve live background crawl orchestrator status metrics."""
    return CRAWL_PROGRESS


@app.post("/api/crawl", tags=["Crawler"])
def start_crawl_pipeline(
    compressor_type: str = Query(None, description="Partial name of compressor type to filter"),
    no_cache: bool = Query(False, description="Bypass local web cache files"),
    background_tasks: BackgroundTasks = None
):
    """Trigger background crawler task saving directly to PostgreSQL."""
    if CRAWL_PROGRESS["active"]:
        raise HTTPException(status_code=400, detail="A crawling background task is already active.")
        
    # Launch background job
    background_tasks.add_task(run_crawling_background, compressor_type, no_cache)
    return {"status": "started", "message": "Crawler pipeline started successfully in background."}


@app.post("/api/crawl/discover-brands", tags=["Crawler"])
def discover_brands(
    compressor_type: str = Query(None, description="Partial name of compressor type to filter"),
    no_cache: bool = Query(False, description="Bypass local web cache files"),
    background_tasks: BackgroundTasks = None
):
    """Trigger brand discovery crawler (Stage 1 ONLY) in background."""
    if CRAWL_PROGRESS["active"]:
        raise HTTPException(status_code=400, detail="A crawling background task is already active.")
        
    background_tasks.add_task(run_brand_discovery_background, compressor_type, no_cache)
    return {"status": "started", "message": "Brand discovery pipeline started in background."}


@app.post("/api/crawl/harvest-specs", tags=["Crawler"])
def harvest_specs(
    no_cache: bool = Query(False, description="Bypass local web cache files"),
    background_tasks: BackgroundTasks = None
):
    """Trigger specifications crawler (Stage 2 and 3) for approved brands ONLY."""
    if CRAWL_PROGRESS["active"]:
        raise HTTPException(status_code=400, detail="A crawling background task is already active.")
        
    background_tasks.add_task(run_specs_harvester_background, no_cache)
    return {"status": "started", "message": "Specifications harvester pipeline started for approved brands."}


@app.get("/api/manufacturers", tags=["Data"])
def list_manufacturers(db: Session = Depends(connection.get_db)):
    """List all manufacturers with their approval status and model counts."""
    mfrs = db.query(Manufacturer).order_by(Manufacturer.name.asc()).all()
    return [
        {
            "id": m.id,
            "name": m.name,
            "country": m.country,
            "website": m.website,
            "description": m.description,
            "is_approved": m.is_approved,
            "model_count": db.query(Model).filter(Model.manufacturer_id == m.id).count()
        }
        for m in mfrs
    ]


@app.put("/api/manufacturers/{manufacturer_id}/approve", tags=["Data"])
def approve_manufacturer(
    manufacturer_id: int,
    is_approved: bool = Query(..., description="Set approval status"),
    db: Session = Depends(connection.get_db)
):
    """Toggle a manufacturer's approval status (is_approved)."""
    mfr = db.query(Manufacturer).filter(Manufacturer.id == manufacturer_id).first()
    if not mfr:
        raise HTTPException(status_code=404, detail="Manufacturer not found")
        
    mfr.is_approved = is_approved
    db.commit()
    db.refresh(mfr)
    
    status_word = "approved" if is_approved else "unapproved"
    return {"status": "success", "message": f"Brand '{mfr.name}' has been successfully {status_word}!"}


@app.get("/api/crawl/history", tags=["Crawler"])
def get_crawl_history(db: Session = Depends(connection.get_db)):
    """Retrieve historical logs for all background crawl runs."""
    history = db.query(CrawlHistory).order_by(CrawlHistory.started_at.desc()).all()
    return [
        {
            "id": h.id,
            "started_at": h.started_at.isoformat() if h.started_at else None,
            "completed_at": h.completed_at.isoformat() if h.completed_at else None,
            "status": h.status,
            "compressor_type": h.compressor_type,
            "new_manufacturers_count": h.new_manufacturers_count,
            "new_models_count": h.new_models_count,
            "total_specs_enriched": h.total_specs_enriched,
            "log_message": h.log_message
        }
        for h in history
    ]


@app.get("/api/compressors", tags=["Data"])
def get_all_compressor_data(db: Session = Depends(connection.get_db)):
    """Return nested category tree of compressor types -> manufacturers -> models."""
    types = db.query(CompressorType).all()
    tree = []
    
    for t in types:
        mfrs = db.query(Manufacturer).join(Model).filter(Model.type_id == t.id).distinct().all()
        mfr_list = []
        for m in mfrs:
            models = db.query(Model).filter(Model.type_id == t.id, Model.manufacturer_id == m.id).all()
            mfr_list.append({
                "id": m.id,
                "name": m.name,
                "country": m.country,
                "website": m.website,
                "models": [{"id": mo.id, "model_name": mo.model_name, "series": mo.series} for mo in models]
            })
            
        tree.append({
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "manufacturers": mfr_list
        })
    return tree


@app.get("/api/models", tags=["Data"])
def list_compressor_models(
    q: str = Query(None, description="Filter by model name or series"),
    manufacturer_id: int = Query(None),
    type_id: int = Query(None),
    db: Session = Depends(connection.get_db)
):
    """List compressor models with active filter options."""
    query = db.query(Model)
    if q:
        query = query.filter(Model.model_name.ilike(f"%{q}%") | Model.series.ilike(f"%{q}%"))
    if manufacturer_id:
        query = query.filter(Model.manufacturer_id == manufacturer_id)
    if type_id:
        query = query.filter(Model.type_id == type_id)
        
    models = query.all()
    return [
        {
            "id": mo.id,
            "model_name": mo.model_name,
            "series": mo.series,
            "product_url": mo.product_url,
            "manufacturer": mo.manufacturer.name,
            "compressor_type": mo.compressor_type.name,
        }
        for mo in models
    ]


@app.get("/api/models/{model_id}", tags=["Data"])
def get_model_specifications(model_id: int, db: Session = Depends(connection.get_db)):
    """Retrieve full engineering attributes specs sheet for a specific model."""
    model = db.query(Model).filter(Model.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
        
    attr_record = db.query(TechnicalAttribute).filter(TechnicalAttribute.model_id == model_id).first()
    attributes = attr_record.attributes if attr_record else {}
    
    return {
        "id": model.id,
        "model_name": model.model_name,
        "series": model.series,
        "product_url": model.product_url,
        "compressor_type": model.compressor_type.name,
        "manufacturer": {
            "name": model.manufacturer.name,
            "country": model.manufacturer.country,
            "website": model.manufacturer.website,
            "description": model.manufacturer.description
        },
        "attributes": attributes,
        "updated_at": attr_record.updated_at.isoformat() if attr_record else None
    }


# ── CLI Core Helpers ───────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Compressor Data Crawler -- Discovers manufacturers, models, and specs",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--stage", "-s",
        nargs="+",
        type=int,
        choices=[1, 2, 3],
        default=[1, 2, 3],
        help="Which stages to run (default: all three)",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable file cache (re-crawl everything)",
    )
    parser.add_argument(
        "--type", "-t",
        nargs="+",
        help="Filter to specific compressor types (partial match OK)",
    )
    parser.add_argument(
        "--input", "-i",
        default=None,
        help=f"Path to compressors JSON input file (default: {COMPRESSORS_JSON})",
    )
    parser.add_argument(
        "--server",
        action="store_true",
        help="Start the FastAPI backend server instead of running the CLI",
    )
    return parser.parse_args()


def validate_env():
    errors = []
    if not GEMINI_API_KEY:
        errors.append("  ✗ GEMINI_API_KEY not set in .env")
    if not TAVILY_API_KEY:
        print("  ⚠  TAVILY_API_KEY not set — will use DuckDuckGo fallback")
    if errors:
        print("\n[ERROR] Missing required configuration:")
        for e in errors:
            print(e)
        print("\nPlease copy .env.example to .env and fill in your API keys.")
        sys.exit(1)


def load_json(path: str) -> dict | list:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_compressors(input_path: str | None) -> list:
    path = input_path or COMPRESSORS_JSON
    if not os.path.exists(path):
        print(f"[ERROR] Compressors input file not found: {path}")
        sys.exit(1)
    data = load_json(path)
    if not isinstance(data, list) or not data:
        print(f"[ERROR] Compressors JSON must be a non-empty array: {path}")
        sys.exit(1)
    return data


def filter_compressors(compressors_list: list, type_filters: list | None) -> list:
    if not type_filters:
        return compressors_list
    return [
        c for c in compressors_list
        if any(f.lower() in c["type"].lower() for f in type_filters)
    ]


def print_banner():
    print()
    print("=" * 62)
    print("   Compressor Data Crawler")
    print("   Manufacturer -> Model -> Attributes  |  Powered by Gemini")
    print("=" * 62)
    print()


def print_summary(final_records: list):
    print("\n" + "═" * 60)
    print("  PIPELINE COMPLETE — Summary")
    print("═" * 60)

    by_type = {}
    for r in final_records:
        ctype = r["compressor_type"]
        by_type.setdefault(ctype, []).append(r)

    for ctype, records in by_type.items():
        mfrs = list({r["manufacturer"] for r in records})
        with_attrs = sum(1 for r in records if r.get("attributes"))
        print(f"\n  📦 {ctype}")
        print(f"     Manufacturers : {len(mfrs)}")
        print(f"     Models        : {len(records)}")
        print(f"     With Attrs    : {with_attrs}/{len(records)}")

    print(f"\n  📁 Output file: {FINAL_OUTPUT_JSON}")
    print(f"  📊 Total records: {len(final_records)}")


# ── Entry Point (CLI vs Server) ─────────────────────────────────────────────

def main():
    args = parse_args()

    # Mode A: Start FastAPI Web Server
    if args.server:
        import uvicorn
        print("🚀 Starting FastAPI Server on http://0.0.0.0:8000...")
        print("📖 Access Interactive Swagger Docs at http://127.0.0.1:8000/docs\n")
        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
        return

    # Mode B: Run standard CLI Pipeline
    print_banner()

    if args.no_cache:
        import config
        config.CACHE_ENABLED = False
        print("  ⚠  Cache disabled for this run\n")

    validate_env()
    compressors = load_compressors(args.input)
    target_compressors = filter_compressors(compressors, args.type)
    
    if not target_compressors:
        print(f"[ERROR] No compressor types matched filter: {args.type}")
        sys.exit(1)

    stages_to_run = sorted(set(args.stage))
    print(f"  Stages     : {stages_to_run}")
    print(f"  Types      : {[c['type'] for c in target_compressors]}")
    print(f"  Cache      : {'ON' if CACHE_ENABLED else 'OFF'}")
    print(f"  Started at : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    start_time = time.time()

    # Stage 1
    manufacturers_data = None
    if 1 in stages_to_run:
        manufacturers_data = stage1.run(target_compressors)
    elif 2 in stages_to_run or 3 in stages_to_run:
        print("\n📂 Loading existing manufacturers.json...")
        try:
            manufacturers_data = load_json(MANUFACTURERS_JSON)
            if args.type:
                manufacturers_data = {
                    k: v for k, v in manufacturers_data.items()
                    if any(f.lower() in k.lower() for f in args.type)
                }
        except FileNotFoundError:
            print("[ERROR] manufacturers.json not found. Run Stage 1 first.")
            sys.exit(1)

    # Stage 2
    models_data = None
    if 2 in stages_to_run and manufacturers_data:
        models_data = stage2.run(manufacturers_data)
    elif 3 in stages_to_run:
        print("\n📂 Loading existing models.json...")
        try:
            models_data = load_json(MODELS_JSON)
        except FileNotFoundError:
            print("[ERROR] models.json not found. Run Stage 2 first.")
            sys.exit(1)

    # Stage 3
    final_records = None
    if 3 in stages_to_run and models_data:
        final_records = stage3.run(models_data)
        print_summary(final_records)

    elapsed = time.time() - start_time
    print(f"\n⏱  Total time: {elapsed:.1f}s ({elapsed/60:.1f} min)")
    print("✅ Done!\n")


if __name__ == "__main__":
    main()
