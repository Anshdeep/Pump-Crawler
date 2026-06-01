from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
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

# ── REST Endpoints ─────────────────────────────────────────────────────────

@router.get("/manufacturers")
def list_manufacturers(
    equipment_master_id: int = Query(None),
    equipment_type_id: int = Query(None),
    equipment_subtype_id: int = Query(None),
    page: int = Query(None, description="Page number for pagination"),
    limit: int = Query(10, description="Items per page"),
    db: Session = Depends(get_db)
):
    """List manufacturers in the directory with optional pagination, filtering, and model counts."""
    query = db.query(Manufacturer)
    
    # Filter manufacturers by their associated models' categories
    if equipment_master_id or equipment_type_id or equipment_subtype_id:
        query = query.join(Model, Model.manufacturer_id == Manufacturer.id)
        if equipment_master_id:
            query = query.filter(Model.equipment_master_id == equipment_master_id)
        if equipment_type_id:
            query = query.filter(Model.equipment_type_id == equipment_type_id)
        if equipment_subtype_id:
            query = query.filter(Model.equipment_subtype_id == equipment_subtype_id)
        query = query.distinct()
        
    query = query.order_by(Manufacturer.name.asc())
    
    if page is not None:
        total = query.count()
        mfrs = query.offset((page - 1) * limit).limit(limit).all()
        items = [
            {
                "id": m.id,
                "name": m.name,
                "country": m.country,
                "website": m.website,
                "founded_year": m.founded_year,
                "description": m.description,
                "is_approved": m.is_approved,
                "is_harvested": m.is_harvested,
                "model_count": db.query(Model).filter(Model.manufacturer_id == m.id).count(),
                "created_at": m.created_at,
                "updated_at": m.updated_at
            }
            for m in mfrs
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
                "id": m.id,
                "name": m.name,
                "country": m.country,
                "website": m.website,
                "founded_year": m.founded_year,
                "description": m.description,
                "is_approved": m.is_approved,
                "is_harvested": m.is_harvested,
                "model_count": db.query(Model).filter(Model.manufacturer_id == m.id).count(),
                "created_at": m.created_at,
                "updated_at": m.updated_at
            }
            for m in mfrs
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
