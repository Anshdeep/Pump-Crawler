from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from database.connection import get_db
from database.models import Model, TechnicalAttribute, EquipmentType, Manufacturer, EquipmentMaster
import database.crud as crud

router = APIRouter()

# ── Pydantic Request Validation Models ─────────────────────────────────────

class ModelCreateSchema(BaseModel):
    model_name: str
    equipment_master_id: int
    equipment_type_id: int
    equipment_subtype_id: Optional[int] = None
    manufacturer_id: int
    series: Optional[str] = None
    product_url: Optional[str] = None

# ── REST Endpoints ─────────────────────────────────────────────────────────

@router.get("/models")
def list_equipment_models(
    q: str = Query(None, description="Search by model name or series line"),
    manufacturer_id: int = Query(None),
    equipment_type_id: int = Query(None),
    equipment_master_id: int = Query(None),
    is_approved: bool = Query(None),
    is_harvested: bool = Query(None),
    db: Session = Depends(get_db)
):
    """List all equipment models based on search filters (category, manufacturer, approval, and harvested flags)."""
    query = db.query(Model)
    if q:
        query = query.filter(Model.model_name.ilike(f"%{q}%") | Model.series.ilike(f"%{q}%"))
    if manufacturer_id:
        query = query.filter(Model.manufacturer_id == manufacturer_id)
    if equipment_type_id:
        query = query.filter(Model.equipment_type_id == equipment_type_id)
    if equipment_master_id:
        query = query.filter(Model.equipment_master_id == equipment_master_id)
    if is_approved is not None:
        query = query.filter(Model.is_approved == is_approved)
    if is_harvested is not None:
        query = query.filter(Model.is_harvested == is_harvested)
        
    models = query.order_by(Model.model_name.asc()).all()
    return [
        {
            "id": mo.id,
            "model_name": mo.model_name,
            "series": mo.series,
            "product_url": mo.product_url,
            "is_approved": mo.is_approved,
            "is_harvested": mo.is_harvested,
            "manufacturer": mo.manufacturer.name,
            "manufacturer_id": mo.manufacturer_id,
            "equipment_master": mo.equipment_master.name if mo.equipment_master else "Compressor",
            "equipment_type": mo.equipment_type.name,
            "created_at": mo.created_at,
        }
        for mo in models
    ]

@router.post("/models")
def create_model(data: ModelCreateSchema, db: Session = Depends(get_db)):
    """Manually add a model line into the specs store."""
    master = db.query(EquipmentMaster).filter(EquipmentMaster.id == data.equipment_master_id).first()
    if not master:
        raise HTTPException(status_code=404, detail="Equipment master not found.")
    etype = db.query(EquipmentType).filter(EquipmentType.id == data.equipment_type_id).first()
    if not etype:
        raise HTTPException(status_code=404, detail="Equipment type not found.")
    mfr = db.query(Manufacturer).filter(Manufacturer.id == data.manufacturer_id).first()
    if not mfr:
        raise HTTPException(status_code=404, detail="Manufacturer profile not found.")
        
    existing = db.query(Model).filter(
        Model.equipment_type_id == data.equipment_type_id,
        Model.manufacturer_id == data.manufacturer_id,
        Model.model_name.ilike(data.model_name)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="This model already exists in the specs directory.")
        
    return crud.create_equipment_model(
        db,
        equipment_master_id=data.equipment_master_id,
        equipment_type_id=data.equipment_type_id,
        equipment_subtype_id=data.equipment_subtype_id,
        manufacturer_id=data.manufacturer_id,
        model_name=data.model_name,
        series=data.series,
        product_url=data.product_url
    )

@router.delete("/models/{id}")
def delete_model(id: int, db: Session = Depends(get_db)):
    """Delete a model and its associated technical attribute spec sheets."""
    mo = db.query(Model).filter(Model.id == id).first()
    if not mo:
        raise HTTPException(status_code=404, detail="Equipment model not found.")
    db.delete(mo)
    db.commit()
    return {"status": "success", "message": f"Model '{mo.model_name}' deleted."}

@router.get("/models/{model_id}")
def get_model_specifications(model_id: int, db: Session = Depends(get_db)):
    """Retrieve full engineering attributes spec sheet for a specific model."""
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
        "is_approved": model.is_approved,
        "is_harvested": model.is_harvested,
        "equipment_master": model.equipment_master.name if model.equipment_master else "Compressor",
        "equipment_type": model.equipment_type.name,
        "manufacturer": {
            "id": model.manufacturer.id,
            "name": model.manufacturer.name,
            "country": model.manufacturer.country,
            "website": model.manufacturer.website,
            "description": model.manufacturer.description
        },
        "attributes": attributes,
        "updated_at": attr_record.updated_at.isoformat() if attr_record and attr_record.updated_at else None
    }

@router.put("/models/{model_id}/approve")
def approve_equipment_model(
    model_id: int,
    is_approved: bool = Query(..., description="Set approval switch state"),
    db: Session = Depends(get_db)
):
    """Toggle a model's catalog approval status (is_approved)."""
    model = db.query(Model).filter(Model.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Equipment model not found")
        
    model.is_approved = is_approved
    db.commit()
    db.refresh(model)
    
    status_word = "approved" if is_approved else "unapproved"
    return {"status": "success", "message": f"Model '{model.model_name}' has been {status_word}!"}

class BulkApproveSchema(BaseModel):
    model_ids: List[int]
    is_approved: bool

@router.put("/models/bulk-approve")
def bulk_approve_models(data: BulkApproveSchema, db: Session = Depends(get_db)):
    """Approve or unapprove multiple equipment models at once."""
    if not data.model_ids:
        return {"status": "success", "message": "No models specified."}
    db.query(Model).filter(Model.id.in_(data.model_ids)).update({"is_approved": data.is_approved}, synchronize_session=False)
    db.commit()
    return {"status": "success", "message": f"Successfully updated approval status for {len(data.model_ids)} models."}
