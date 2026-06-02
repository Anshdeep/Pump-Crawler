from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from database.connection import get_db
from database.models import Manufacturer, Model
import database.crud as crud

router = APIRouter()

# ── Pydantic Validation Models ─────────────────────────────────────────────

class ManufacturerSchema(BaseModel):
    name: str
    country: Optional[str] = None
    website: Optional[str] = None
    founded_year: Optional[int] = None
    description: Optional[str] = None

class BulkDeleteSchema(BaseModel):
    ids: List[int]

# ── REST Endpoints ─────────────────────────────────────────────────────────

@router.get("/manufacturers")
def list_manufacturers(
    equipment_master_id: int = Query(None),
    equipment_type_id: int = Query(None),
    equipment_subtype_id: int = Query(None),
    page: int = Query(None, description="Page number for pagination"),
    limit: int = Query(10, description="Items per page"),
    sort_by: str = Query("name", description="Column to sort by"),
    sort_desc: bool = Query(False, description="Sort descending if true"),
    db: Session = Depends(get_db)
):
    """List manufacturers in the directory with optional pagination, filtering, model counts, and sorting."""
    from sqlalchemy import func
    
    # Subquery to calculate model count per manufacturer (excluding placeholders)
    model_count_sub = db.query(
        Model.manufacturer_id,
        func.count(Model.id).label("model_count")
    ).filter(Model.model_name != "TEMP_PLACEHOLDER").group_by(Model.manufacturer_id).subquery()
    
    # Base query selecting Manufacturer and the model count
    query = db.query(
        Manufacturer,
        func.coalesce(model_count_sub.c.model_count, 0).label("model_count")
    ).outerjoin(
        model_count_sub,
        Manufacturer.id == model_count_sub.c.manufacturer_id
    )
    
    # Filter manufacturers by their associated models' categories using IN subquery to avoid duplicates
    if equipment_master_id or equipment_type_id or equipment_subtype_id:
        sub = db.query(Model.manufacturer_id)
        if equipment_master_id:
            sub = sub.filter(Model.equipment_master_id == equipment_master_id)
        if equipment_type_id:
            sub = sub.filter(Model.equipment_type_id == equipment_type_id)
        if equipment_subtype_id:
            sub = sub.filter(Model.equipment_subtype_id == equipment_subtype_id)
        query = query.filter(Manufacturer.id.in_(sub))

    # Determine sorting column
    if sort_by == "model_count":
        sort_col = func.coalesce(model_count_sub.c.model_count, 0)
    elif sort_by == "country":
        sort_col = Manufacturer.country
    elif sort_by == "website":
        sort_col = Manufacturer.website
    elif sort_by == "founded_year":
        sort_col = Manufacturer.founded_year
    elif sort_by == "is_approved":
        sort_col = Manufacturer.is_approved
    elif sort_by == "is_harvested":
        sort_col = Manufacturer.is_harvested
    elif sort_by == "created_at":
        sort_col = Manufacturer.created_at
    else:
        sort_col = Manufacturer.name

    if sort_desc:
        query = query.order_by(sort_col.desc())
    else:
        query = query.order_by(sort_col.asc())
        
    # Secondary order to keep pagination deterministic
    query = query.order_by(Manufacturer.id.asc())

    if page is not None:
        total = query.count()
        mfrs = query.offset((page - 1) * limit).limit(limit).all()
        items = [
            {
                "id": row.Manufacturer.id,
                "name": row.Manufacturer.name,
                "country": row.Manufacturer.country,
                "website": row.Manufacturer.website,
                "founded_year": row.Manufacturer.founded_year,
                "description": row.Manufacturer.description,
                "is_approved": row.Manufacturer.is_approved,
                "is_harvested": row.Manufacturer.is_harvested,
                "model_count": row.model_count,
                "created_at": row.Manufacturer.created_at,
                "updated_at": row.Manufacturer.updated_at
            }
            for row in mfrs
        ]
        return {
            "total": total,
            "page": page,
            "limit": limit,
            "items": items
        }
    else:
        mfrs = query.all()
        return [
            {
                "id": row.Manufacturer.id,
                "name": row.Manufacturer.name,
                "country": row.Manufacturer.country,
                "website": row.Manufacturer.website,
                "founded_year": row.Manufacturer.founded_year,
                "description": row.Manufacturer.description,
                "is_approved": row.Manufacturer.is_approved,
                "is_harvested": row.Manufacturer.is_harvested,
                "model_count": row.model_count,
                "created_at": row.Manufacturer.created_at,
                "updated_at": row.Manufacturer.updated_at
            }
            for row in mfrs
        ]

@router.post("/manufacturers")
def create_manufacturer(data: ManufacturerSchema, db: Session = Depends(get_db)):
    """Manually insert a new manufacturer profile into the registry."""
    existing = db.query(Manufacturer).filter(Manufacturer.name.ilike(data.name)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Manufacturer profile with this name already exists.")
    mfr = crud.get_or_create_manufacturer(
        db,
        name=data.name,
        country=data.country,
        website=data.website,
        description=data.description
    )
    if data.founded_year:
        mfr.founded_year = data.founded_year
        db.commit()
        db.refresh(mfr)
    return mfr

@router.put("/manufacturers/{id}")
def update_manufacturer(id: int, data: ManufacturerSchema, db: Session = Depends(get_db)):
    """Modify manufacturer registration fields."""
    mfr = db.query(Manufacturer).filter(Manufacturer.id == id).first()
    if not mfr:
        raise HTTPException(status_code=404, detail="Manufacturer profile not found.")
    
    mfr.name = data.name
    mfr.country = data.country
    mfr.website = data.website
    mfr.founded_year = data.founded_year
    mfr.description = data.description
    db.commit()
    db.refresh(mfr)
    return mfr

@router.delete("/manufacturers/{id}")
def delete_manufacturer(id: int, db: Session = Depends(get_db)):
    """Delete a manufacturer profile and all its associated models."""
    mfr = db.query(Manufacturer).filter(Manufacturer.id == id).first()
    if not mfr:
        raise HTTPException(status_code=404, detail="Manufacturer profile not found.")
    db.delete(mfr)
    db.commit()
    return {"status": "success", "message": f"Manufacturer '{mfr.name}' deleted successfully."}

@router.post("/manufacturers/bulk-delete")
def bulk_delete_manufacturers(data: BulkDeleteSchema, db: Session = Depends(get_db)):
    """Delete multiple manufacturer profiles and all their associated models."""
    if not data.ids:
        return {"status": "success", "message": "No manufacturers provided to delete."}
    
    mfrs = db.query(Manufacturer).filter(Manufacturer.id.in_(data.ids)).all()
    count = len(mfrs)
    for mfr in mfrs:
        db.delete(mfr)
    db.commit()
    return {"status": "success", "message": f"Successfully deleted {count} manufacturers."}

@router.put("/manufacturers/{id}/approve")
def approve_manufacturer(
    id: int,
    is_approved: bool = Query(..., description="Set approval toggle state"),
    db: Session = Depends(get_db)
):
    """Toggle a manufacturer's crawl approval switch (is_approved)."""
    mfr = db.query(Manufacturer).filter(Manufacturer.id == id).first()
    if not mfr:
        raise HTTPException(status_code=404, detail="Manufacturer profile not found.")
        
    mfr.is_approved = is_approved
    db.commit()
    db.refresh(mfr)
    
    status_word = "approved" if is_approved else "unapproved"
    return {"status": "success", "message": f"Manufacturer '{mfr.name}' has been {status_word}."}
