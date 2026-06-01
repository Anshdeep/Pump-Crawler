from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date, text
from collections import defaultdict
from database.connection import get_db, init_db
from database.models import SystemSetting, Manufacturer, Model, TechnicalAttribute, EquipmentType, CrawlHistory
import database.crud as crud

router = APIRouter()

@router.post("/init-db")
def initialize_database():
    """Enable pgvector and initialize dynamic taxonomy/settings schemas."""
    try:
        init_db()
        return {"status": "success", "message": "PostgreSQL database taxonomy and system settings initialized!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database initialization failed: {e}")

@router.get("/settings")
def get_settings(db: Session = Depends(get_db)):
    """Retrieve all configurable settings saved inside the database."""
    settings = db.query(SystemSetting).order_by(SystemSetting.key.asc()).all()
    return [
        {
            "key": s.key,
            "value": s.value,
            "value_type": s.value_type,
            "description": s.description
        }
        for s in settings
    ]

@router.put("/settings/{key}")
def update_system_setting(key: str, value: str, db: Session = Depends(get_db)):
    """Update a specific dynamic system setting inside the database."""
    setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if not setting:
        raise HTTPException(status_code=404, detail="System setting not found")
    crud.update_setting(db, key, value)
    return {"status": "success", "message": f"System configuration setting '{key}' updated successfully!"}

@router.get("/dashboard-stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Retrieve highly detailed aggregation metrics for the Overview Dashboard charts."""
    try:
        # 1. Manufacturers metrics
        mfrs_total = db.query(Manufacturer).count()
        mfrs_approved = db.query(Manufacturer).filter(Manufacturer.is_approved == True).count()
        mfrs_pending = mfrs_total - mfrs_approved
        mfrs_harvested = db.query(Manufacturer).filter(Manufacturer.is_harvested == True).count()
        mfrs_unharvested = mfrs_total - mfrs_harvested

        mfrs_by_country = db.query(
            Manufacturer.country,
            func.count(Manufacturer.id).label('count')
        ).group_by(Manufacturer.country).order_by(text('count DESC')).all()

        by_country_list = [
            {"country": c if c else "Unknown", "count": cnt}
            for c, cnt in mfrs_by_country
        ]

        # 2. Models metrics
        models_total = db.query(Model).count()
        models_approved = db.query(Model).filter(Model.is_approved == True).count()
        models_pending = models_total - models_approved
        models_harvested = db.query(Model).filter(Model.is_harvested == True).count()
        models_unharvested = models_total - models_harvested

        models_by_type = db.query(
            EquipmentType.name,
            func.count(Model.id).label('count')
        ).join(Model, Model.equipment_type_id == EquipmentType.id).group_by(EquipmentType.name).order_by(text('count DESC')).all()

        by_type_list = [
            {"type_name": name, "count": cnt}
            for name, cnt in models_by_type
        ]

        # 3. Technical Attributes specs metrics
        enriched_count = db.query(TechnicalAttribute).count()
        unenriched_count = models_total - enriched_count
        enrichment_rate = round((enriched_count / models_total * 100), 1) if models_total > 0 else 0

        # 4. Daily timeline discoveries and harvesting
        models_created = db.query(
            cast(Model.created_at, Date).label('date'),
            func.count(Model.id).label('count')
        ).group_by(cast(Model.created_at, Date)).all()

        models_harvested_by_date = db.query(
            cast(Model.updated_at, Date).label('date'),
            func.count(Model.id).label('count')
        ).filter(Model.is_harvested == True).group_by(cast(Model.updated_at, Date)).all()

        mfrs_created = db.query(
            cast(Manufacturer.created_at, Date).label('date'),
            func.count(Manufacturer.id).label('count')
        ).group_by(cast(Manufacturer.created_at, Date)).all()

        mfrs_harvested_by_date = db.query(
            cast(Manufacturer.updated_at, Date).label('date'),
            func.count(Manufacturer.id).label('count')
        ).filter(Manufacturer.is_harvested == True).group_by(cast(Manufacturer.updated_at, Date)).all()

        timeline_data = defaultdict(lambda: {
            "date": "",
            "discovered_manufacturers": 0,
            "harvested_manufacturers": 0,
            "discovered_models": 0,
            "harvested_models": 0
        })

        for dt, cnt in mfrs_created:
            if dt:
                d_str = dt.isoformat()
                timeline_data[d_str]["date"] = d_str
                timeline_data[d_str]["discovered_manufacturers"] = cnt

        for dt, cnt in mfrs_harvested_by_date:
            if dt:
                d_str = dt.isoformat()
                timeline_data[d_str]["date"] = d_str
                timeline_data[d_str]["harvested_manufacturers"] = cnt

        for dt, cnt in models_created:
            if dt:
                d_str = dt.isoformat()
                timeline_data[d_str]["date"] = d_str
                timeline_data[d_str]["discovered_models"] = cnt

        for dt, cnt in models_harvested_by_date:
            if dt:
                d_str = dt.isoformat()
                timeline_data[d_str]["date"] = d_str
                timeline_data[d_str]["harvested_models"] = cnt

        sorted_timeline = sorted(timeline_data.values(), key=lambda x: x["date"])

        # 5. Crawl run history metrics
        crawl_history = db.query(CrawlHistory).order_by(CrawlHistory.started_at.asc()).all()
        crawl_history_list = [
            {
                "id": h.id,
                "date": h.started_at.isoformat() if h.started_at else None,
                "new_manufacturers": h.new_manufacturers_count,
                "new_models": h.new_models_count,
                "specs_enriched": h.total_specs_enriched,
                "status": h.status
            }
            for h in crawl_history
        ]

        return {
            "manufacturers": {
                "total": mfrs_total,
                "approved": mfrs_approved,
                "pending": mfrs_pending,
                "harvested": mfrs_harvested,
                "unharvested": mfrs_unharvested,
                "by_country": by_country_list
            },
            "models": {
                "total": models_total,
                "approved": models_approved,
                "pending": models_pending,
                "harvested": models_harvested,
                "unharvested": models_unharvested,
                "by_type": by_type_list
            },
            "attributes": {
                "total_models": models_total,
                "enriched": enriched_count,
                "unenriched": unenriched_count,
                "enrichment_rate": enrichment_rate
            },
            "timeline": sorted_timeline,
            "crawl_history": crawl_history_list
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load dashboard statistics: {e}")

