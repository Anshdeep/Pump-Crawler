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
def get_crawl_history(db: Session = Depends(get_db)):
    """Retrieve historical logs for all background crawl operations."""
    history = db.query(CrawlHistory).order_by(CrawlHistory.started_at.desc()).all()
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
    equipment_type_id: int = Query(None, description="Optional Equipment Type ID filter to crawl"),
    no_cache: bool = Query(False, description="Bypass local web cache files"),
    background_tasks: BackgroundTasks = None
):
    """Trigger background crawler task to discover manufacturers (Stage 1)."""
    if orchestrator.CRAWL_PROGRESS["active"]:
        raise HTTPException(status_code=400, detail="A crawling background task is already active.")
        
    background_tasks.add_task(orchestrator.run_manufacturer_discovery_background, equipment_type_id, no_cache)
    return {"status": "started", "message": "Manufacturer discovery pipeline successfully started in background."}

@router.post("/crawl/harvest-specs")
def trigger_specs_harvester(
    manufacturer_ids: List[int] = Query(None, description="Selected list of manufacturer IDs to target"),
    model_ids: List[int] = Query(None, description="Selected list of specific model IDs to target"),
    deep_crawl: bool = Query(True, description="Run Stage 2 model discovery before specs extraction"),
    only_unharvested: bool = Query(False, description="Only target manufacturers/models not previously harvested"),
    no_cache: bool = Query(False, description="Bypass local web cache files"),
    background_tasks: BackgroundTasks = None
):
    """Trigger background specifications harvester for approved manufacturers (Stages 2 & 3)."""
    if orchestrator.CRAWL_PROGRESS["active"]:
        raise HTTPException(status_code=400, detail="A crawling background task is already active.")
        
    background_tasks.add_task(
        orchestrator.run_specs_harvester_background, 
        manufacturer_ids, 
        only_unharvested, 
        no_cache,
        model_ids,
        deep_crawl
    )
    return {"status": "started", "message": "Specifications harvester pipeline successfully started in background."}

@router.post("/crawl/stop")
def stop_crawl():
    """Request active background crawl operation to stop immediately."""
    if not orchestrator.CRAWL_PROGRESS["active"]:
        raise HTTPException(status_code=400, detail="No active crawling task to stop.")
        
    orchestrator.request_crawl_stop()
    return {"status": "stopping", "message": "Stop request successfully sent to the background crawler."}
