"""
main.py -- Industrial Equipment Specs Discovery & RAG Platform
Dual-mode entry point:
  1. Web Server Mode: python main.py --server
  2. CLI Pipeline Mode: python main.py
"""
import os
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from utils.logging_setup import setup_logging
setup_logging("backend.log")

import argparse
import time
from datetime import datetime

# FastAPI Server Imports
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Combined Router & Database Imports
from api.router import api_router
import database.connection as connection
import database.crud as crud
from database.models import EquipmentType

# ── FastAPI App Configuration ──────────────────────────────────────────────

app = FastAPI(
    title="Industrial Equipment Specs Discovery API",
    description="Backend API serving structured equipment technical specifications with pgvector RAG deduplication",
    version="3.0.0"
)

# Enable CORS for frontend dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register modular routers under the /api namespace
app.include_router(api_router, prefix="/api")

@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "Industrial Equipment Specs Discovery & RAG Platform API is online!",
        "documentation": "/docs"
    }

# ── CLI Mode Pipeline Execution ─────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Equipment Crawler CLI Pipeline",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--stage", "-s",
        nargs="+",
        type=int,
        choices=[1, 2, 3],
        default=[1, 2, 3],
        help="Which crawler stages to run (default: all three)",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Bypass local web caching systems",
    )
    parser.add_argument(
        "--type", "-t",
        nargs="+",
        help="Filter to specific equipment types (partial match OK)",
    )
    parser.add_argument(
        "--server",
        action="store_true",
        help="Start the FastAPI backend server instead of running CLI pipeline",
    )
    return parser.parse_args()


def run_cli_pipeline(args):
    print("\n" + "=" * 65)
    print("   Industrial Equipment Specs Discovery CLI Pipeline")
    print("   Powered by Gemini & PostgreSQL Vector Deduplication")
    print("=" * 65 + "\n")

    # Initialize DB schemas
    connection.init_db()
    db = next(connection.get_db())

    # Get dynamic settings from DB
    max_mfrs = crud.get_setting_typed(db, "MAX_MANUFACTURERS_PER_TYPE", 3)
    max_models = crud.get_setting_typed(db, "MAX_MODELS_PER_MANUFACTURER", 5)
    cache_on = False if args.no_cache else crud.get_setting_typed(db, "CACHE_ENABLED", True)
    delay = crud.get_setting_typed(db, "REQUEST_DELAY_SECONDS", 1.5)
    model_name = crud.get_setting(db, "GEMINI_MODEL", "gemini-2.5-flash")
    similarity = crud.get_setting_typed(db, "RAG_SIMILARITY_THRESHOLD", 0.92)

    # Override config values in stages
    import config
    config.CACHE_ENABLED = cache_on
    config.MAX_MANUFACTURERS_PER_TYPE = max_mfrs
    config.MAX_MODELS_PER_MANUFACTURER = max_models
    config.REQUEST_DELAY_SECONDS = delay
    config.GEMINI_MODEL = model_name
    config.RAG_SIMILARITY_THRESHOLD = similarity

    # Fetch equipment types matching user filter
    query_etypes = db.query(EquipmentType)
    if args.type:
        # Match using ILIKE on type name
        from sqlalchemy import or_
        filters = [EquipmentType.name.ilike(f"%{f}%") for f in args.type]
        query_etypes = query_etypes.filter(or_(*filters))
    
    etype_objs = query_etypes.all()
    if not etype_objs:
        print(f"[ERROR] No equipment types found matching filters: {args.type}")
        sys.exit(1)

    print("====================")
    print(etype_objs)
    print("====================")
    
    print(f"  Target Types : {[et.name for et in etype_objs]}")
    print(f"  Stages       : {args.stage}")
    print(f"  Cache        : {'ON' if cache_on else 'OFF'}")
    print(f"  Started at   : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    start_time = time.time()

    # Stage 1: Manufacturers Discovery
    mfrs_data = None
    if 1 in args.stage:
        import stages.stage1_manufacturers as stage1
        equipment_list = []
        for et in etype_objs:
            subtypes = [sub.name for sub in et.subtypes]
            equipment_list.append({
                "id": et.id,
                "type": et.name,
                "equipment_master_id": et.equipment_master_id,
                "subtypes": subtypes,
                "applications": []
            })
        mfrs_data = stage1.run(equipment_list, db=db)
    else:
        # Load from fallback json
        try:
            with open(config.MANUFACTURERS_JSON, "r", encoding="utf-8") as f:
                import json
                mfrs_data = json.load(f)
        except FileNotFoundError:
            print("[ERROR] manufacturers.json not found. Run Stage 1 first.")
            sys.exit(1)

    # Stage 2: Models Discovery
    models_data = None
    if 2 in args.stage and mfrs_data:
        import stages.stage2_models as stage2
        models_data = stage2.run(mfrs_data, db=db)
    else:
        try:
            with open(config.MODELS_JSON, "r", encoding="utf-8") as f:
                import json
                models_data = json.load(f)
        except FileNotFoundError:
            print("[ERROR] models.json not found. Run Stage 2 first.")
            sys.exit(1)

    # Stage 3: Attributes Specs Extraction
    if 3 in args.stage and models_data:
        import stages.stage3_attributes as stage3
        final_records = stage3.run(models_data, db=db)
        
        # Print summary
        print(f"\n  📊 CLI Run Summary:")
        print(f"     Total models processed: {len(final_records)}")
        print(f"     Specs enriched        : {sum(1 for r in final_records if r.get('attributes'))}")

    elapsed = time.time() - start_time
    print(f"\n⏱  Total pipeline time: {elapsed:.1f}s ({elapsed/60:.1f} min)")
    print("✅ Done!\n")
    db.close()


def main():
    args = parse_args()

    # Web Server Mode
    if args.server:
        import uvicorn
        print("🚀 Starting modular FastAPI Server on http://0.0.0.0:8000...")
        print("📖 Access Swagger interactive documentation at http://127.0.0.1:8000/docs\n")
        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
        return

    # CLI Pipeline Mode
    run_cli_pipeline(args)


if __name__ == "__main__":
    main()
