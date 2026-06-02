from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from database.connection import get_db
from database.models import CrawlHistory
import utils.crawler_orchestrator as orchestrator

router = APIRouter()

@router.get("/crawl/status")
def get_crawl_status():
    """Retrieve live real-time metrics and progress percentages for background crawls."""
    return orchestrator.CRAWL_PROGRESS

@router.get("/crawl/history")
def get_crawl_history(
    page: int = Query(None, description="Page number for pagination"),
    limit: int = Query(10, description="Items per page for pagination"),
    db: Session = Depends(get_db)
):
    """Retrieve historical logs for all background crawl operations."""
    query = db.query(CrawlHistory).order_by(CrawlHistory.started_at.desc())
    if page is not None:
        total = query.count()
        offset = (page - 1) * limit
        history = query.offset(offset).limit(limit).all()
        return {
            "total": total,
            "page": page,
            "limit": limit,
            "items": [
                {
                    "id": h.id,
                    "started_at": h.started_at.isoformat() if h.started_at else None,
                    "completed_at": h.completed_at.isoformat() if h.completed_at else None,
                    "status": h.status,
                    "compressor_type": h.compressor_type,  # Categorization target name
                    "new_manufacturers_count": h.new_manufacturers_count,
                    "new_models_count": h.new_models_count,
                    "total_specs_enriched": h.total_specs_enriched,
                    "log_message": h.log_message
                }
                for h in history
            ]
        }
    else:
        history = query.all()
        return [
            {
                "id": h.id,
                "started_at": h.started_at.isoformat() if h.started_at else None,
                "completed_at": h.completed_at.isoformat() if h.completed_at else None,
                "status": h.status,
                "compressor_type": h.compressor_type,  # Categorization target name
                "new_manufacturers_count": h.new_manufacturers_count,
                "new_models_count": h.new_models_count,
                "total_specs_enriched": h.total_specs_enriched,
                "log_message": h.log_message
            }
            for h in history
        ]

@router.post("/crawl/discover-manufacturers")
def trigger_manufacturer_discovery(
    equipment_master_id: int = Query(None, description="Optional Equipment Master ID to scope crawl to a single category (e.g. Pump)"),
    equipment_type_id: int = Query(None, description="Optional Equipment Type ID filter to crawl a single type"),
    no_cache: bool = Query(False, description="Bypass local web cache files"),
    background_tasks: BackgroundTasks = None
):
    """Trigger background crawler task to discover manufacturers (Stage 1)."""
    if orchestrator.CRAWL_PROGRESS["active"]:
        raise HTTPException(status_code=400, detail="A crawling background task is already active.")
        
    background_tasks.add_task(
        orchestrator.run_manufacturer_discovery_background,
        equipment_master_id,
        equipment_type_id,
        no_cache
    )
    return {"status": "started", "message": "Manufacturer discovery pipeline successfully started in background."}

@router.post("/crawl/discover-models")
def trigger_model_discovery(
    manufacturer_ids: List[int] = Query(None, alias="manufacturer_ids", description="Selected list of manufacturer IDs to target"),
    manufacturer_ids_bracket: List[int] = Query(None, alias="manufacturer_ids[]", description="Selected list of manufacturer IDs to target (bracket format)"),
    only_unharvested: bool = Query(False, description="Only target manufacturers not previously harvested"),
    no_cache: bool = Query(False, description="Bypass local web cache files"),
    equipment_master_id: int = Query(None, description="Filter crawl targets by Equipment Master ID"),
    equipment_type_id: int = Query(None, description="Filter crawl targets by Equipment Type ID"),
    equipment_subtype_id: int = Query(None, description="Filter crawl targets by Equipment Subtype ID"),
    background_tasks: BackgroundTasks = None
):
    """Trigger background model lineup discovery for approved manufacturers (Stage 2)."""
    # Merge standard and bracketed manufacturer IDs
    target_mfr_ids = []
    if manufacturer_ids:
        target_mfr_ids.extend(manufacturer_ids)
    if manufacturer_ids_bracket:
        target_mfr_ids.extend(manufacturer_ids_bracket)
    if not target_mfr_ids:
        target_mfr_ids = None

    print(f"[API ROUTE] /crawl/discover-models called with manufacturer_ids={target_mfr_ids}, equipment_master_id={equipment_master_id}, equipment_type_id={equipment_type_id}, equipment_subtype_id={equipment_subtype_id}")
    if orchestrator.CRAWL_PROGRESS["active"]:
        raise HTTPException(status_code=400, detail="A crawling background task is already active.")
        
    background_tasks.add_task(
        orchestrator.run_model_discovery_background, 
        manufacturer_ids=target_mfr_ids, 
        only_unharvested=only_unharvested, 
        no_cache=no_cache,
        equipment_master_id=equipment_master_id,
        equipment_type_id=equipment_type_id,
        equipment_subtype_id=equipment_subtype_id
    )
    return {"status": "started", "message": "Model discovery pipeline successfully started in background."}

@router.post("/crawl/harvest-specs")
def trigger_specs_harvester(
    manufacturer_ids: List[int] = Query(None, alias="manufacturer_ids", description="Selected list of manufacturer IDs to target"),
    manufacturer_ids_bracket: List[int] = Query(None, alias="manufacturer_ids[]", description="Selected list of manufacturer IDs to target (bracket format)"),
    model_ids: List[int] = Query(None, alias="model_ids", description="Selected list of specific model IDs to target"),
    model_ids_bracket: List[int] = Query(None, alias="model_ids[]", description="Selected list of specific model IDs to target (bracket format)"),
    deep_crawl: bool = Query(False, description="Run Stage 2 model discovery before specs extraction"),
    only_unharvested: bool = Query(False, description="Only target manufacturers/models not previously harvested"),
    no_cache: bool = Query(False, description="Bypass local web cache files"),
    equipment_master_id: int = Query(None, description="Filter crawl targets by Equipment Master ID"),
    equipment_type_id: int = Query(None, description="Filter crawl targets by Equipment Type ID"),
    equipment_subtype_id: int = Query(None, description="Filter crawl targets by Equipment Subtype ID"),
    target_approved_only: bool = Query(True, description="Only extract specs for approved models"),
    background_tasks: BackgroundTasks = None
):
    """Trigger background specifications harvester for approved manufacturers (Stages 2 & 3)."""
    # Merge standard and bracketed manufacturer IDs
    target_mfr_ids = []
    if manufacturer_ids:
        target_mfr_ids.extend(manufacturer_ids)
    if manufacturer_ids_bracket:
        target_mfr_ids.extend(manufacturer_ids_bracket)
    if not target_mfr_ids:
        target_mfr_ids = None

    # Merge standard and bracketed model IDs
    target_model_ids = []
    if model_ids:
        target_model_ids.extend(model_ids)
    if model_ids_bracket:
        target_model_ids.extend(model_ids_bracket)
    if not target_model_ids:
        target_model_ids = None

    print(f"[API ROUTE] /crawl/harvest-specs called with manufacturer_ids={target_mfr_ids}, model_ids={target_model_ids}, deep_crawl={deep_crawl}, equipment_master_id={equipment_master_id}, equipment_type_id={equipment_type_id}, equipment_subtype_id={equipment_subtype_id}, target_approved_only={target_approved_only}")
    if orchestrator.CRAWL_PROGRESS["active"]:
        raise HTTPException(status_code=400, detail="A crawling background task is already active.")
        
    background_tasks.add_task(
        orchestrator.run_specs_harvester_background, 
        manufacturer_ids=target_mfr_ids, 
        only_unharvested=only_unharvested, 
        no_cache=no_cache,
        model_ids=target_model_ids,
        deep_crawl=deep_crawl,
        equipment_master_id=equipment_master_id,
        equipment_type_id=equipment_type_id,
        equipment_subtype_id=equipment_subtype_id,
        target_approved_only=target_approved_only
    )
    return {"status": "started", "message": "Specifications harvester pipeline successfully started in background."}

@router.post("/crawl/stop")
def stop_crawl():
    """Request active background crawl operation to stop immediately."""
    if not orchestrator.CRAWL_PROGRESS["active"]:
        raise HTTPException(status_code=400, detail="No active crawling task to stop.")
        
    orchestrator.request_crawl_stop()
    return {"status": "stopping", "message": "Stop request successfully sent to the background crawler."}
