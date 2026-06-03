from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from database.connection import get_db
from database.models import EquipmentMaster, EquipmentType, EquipmentSubtype, Manufacturer, Model
import database.crud as crud

router = APIRouter()

# ── Pydantic Request Validation Models ─────────────────────────────────────

class MasterSchema(BaseModel):
    name: str
    description: Optional[str] = None

class TypeSchema(BaseModel):
    name: str
    equipment_master_id: int
    description: Optional[str] = None

class SubtypeSchema(BaseModel):
    name: str
    type_id: int

# ── Equipment Master Endpoints ──────────────────────────────────────────────

@router.get("/equipment-masters")
def list_equipment_masters(db: Session = Depends(get_db)):
    """Retrieve all high-level equipment master categories (e.g. Pump, Compressor)."""
    return db.query(EquipmentMaster).order_by(EquipmentMaster.name.asc()).all()

@router.post("/equipment-masters")
def create_equipment_master(data: MasterSchema, db: Session = Depends(get_db)):
    """Create a new high-level equipment master category."""
    existing = db.query(EquipmentMaster).filter(EquipmentMaster.name.ilike(data.name)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Equipment master with this name already exists.")
    return crud.get_or_create_equipment_master(db, data.name, data.description)

@router.put("/equipment-masters/{id}")
def update_equipment_master(id: int, data: MasterSchema, db: Session = Depends(get_db)):
    """Modify an existing equipment master category."""
    obj = db.query(EquipmentMaster).filter(EquipmentMaster.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Equipment master category not found.")
    obj.name = data.name
    obj.description = data.description
    db.commit()
    db.refresh(obj)
    return obj

@router.delete("/equipment-masters/{id}")
def delete_equipment_master(id: int, db: Session = Depends(get_db)):
    """Remove an equipment master category."""
    obj = db.query(EquipmentMaster).filter(EquipmentMaster.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Equipment master category not found.")
    db.delete(obj)
    db.commit()
    return {"status": "success", "message": f"Equipment master category '{obj.name}' deleted."}

# ── Equipment Type Endpoints ────────────────────────────────────────────────

@router.get("/equipment-types")
def list_equipment_types(db: Session = Depends(get_db)):
    """Retrieve all specific equipment categories (e.g. Air Compressors, Centrifugal Pumps)."""
    return db.query(EquipmentType).order_by(EquipmentType.name.asc()).all()

@router.post("/equipment-types")
def create_equipment_type(data: TypeSchema, db: Session = Depends(get_db)):
    """Create a new equipment type category under a master category."""
    master = db.query(EquipmentMaster).filter(EquipmentMaster.id == data.equipment_master_id).first()
    if not master:
        raise HTTPException(status_code=404, detail="Parent equipment master category not found.")
    existing = db.query(EquipmentType).filter(
        EquipmentType.name.ilike(data.name),
        EquipmentType.equipment_master_id == data.equipment_master_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Equipment type already exists under this master category.")
    return crud.get_or_create_equipment_type(db, data.name, data.equipment_master_id, data.description)

@router.put("/equipment-types/{id}")
def update_equipment_type(id: int, data: TypeSchema, db: Session = Depends(get_db)):
    """Update an equipment type category."""
    obj = db.query(EquipmentType).filter(EquipmentType.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Equipment type category not found.")
    master = db.query(EquipmentMaster).filter(EquipmentMaster.id == data.equipment_master_id).first()
    if not master:
        raise HTTPException(status_code=404, detail="Parent equipment master category not found.")
    obj.name = data.name
    obj.equipment_master_id = data.equipment_master_id
    obj.description = data.description
    db.commit()
    db.refresh(obj)
    return obj

@router.delete("/equipment-types/{id}")
def delete_equipment_type(id: int, db: Session = Depends(get_db)):
    """Remove an equipment type category."""
    obj = db.query(EquipmentType).filter(EquipmentType.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Equipment type category not found.")
    db.delete(obj)
    db.commit()
    return {"status": "success", "message": f"Equipment type category '{obj.name}' deleted."}

# ── Equipment Subtypes Endpoints ───────────────────────────────────────────

@router.get("/equipment-subtypes")
def list_equipment_subtypes(db: Session = Depends(get_db)):
    """Retrieve all specific subtypes (e.g. Scroll, Plunger)."""
    return db.query(EquipmentSubtype).order_by(EquipmentSubtype.name.asc()).all()

@router.post("/equipment-subtypes")
def create_equipment_subtype(data: SubtypeSchema, db: Session = Depends(get_db)):
    """Create a new subtype under a parent equipment type."""
    parent = db.query(EquipmentType).filter(EquipmentType.id == data.type_id).first()
    if not parent:
        raise HTTPException(status_code=404, detail="Parent equipment type not found.")
    existing = db.query(EquipmentSubtype).filter(
        EquipmentSubtype.name.ilike(data.name),
        EquipmentSubtype.type_id == data.type_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Subtype already exists under this equipment type category.")
    return crud.get_or_create_equipment_subtype(db, data.name, data.type_id)

@router.put("/equipment-subtypes/{id}")
def update_equipment_subtype(id: int, data: SubtypeSchema, db: Session = Depends(get_db)):
    """Update a specific equipment subtype."""
    obj = db.query(EquipmentSubtype).filter(EquipmentSubtype.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Equipment subtype not found.")
    parent = db.query(EquipmentType).filter(EquipmentType.id == data.type_id).first()
    if not parent:
        raise HTTPException(status_code=404, detail="Parent equipment type category not found.")
    obj.name = data.name
    obj.type_id = data.type_id
    db.commit()
    db.refresh(obj)
    return obj

@router.delete("/equipment-subtypes/{id}")
def delete_equipment_subtype(id: int, db: Session = Depends(get_db)):
    """Remove an equipment subtype."""
    obj = db.query(EquipmentSubtype).filter(EquipmentSubtype.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Equipment subtype not found.")
    db.delete(obj)
    db.commit()
    return {"status": "success", "message": f"Equipment subtype '{obj.name}' deleted."}

# ── Taxonomy Tree Compatibility Endpoints ────────────────────────────────────

@router.get("/taxonomy/tree")
def get_taxonomy_tree(db: Session = Depends(get_db)):
    """Retrieve complete nested taxonomy tree of Master -> Type -> Manufacturer -> Model, plus Subtypes and timestamps."""
    masters = db.query(EquipmentMaster).all()
    tree = []
    for m in masters:
        type_list = []
        for t in m.types:
            # Retrieve subtypes for this equipment type
            subtypes_list = [
                {
                    "id": s.id,
                    "name": s.name,
                    "type_id": s.type_id,
                    "created_at": s.created_at,
                    "updated_at": s.updated_at
                }
                for s in t.subtypes
            ]
            
            mfrs = db.query(Manufacturer).join(Model).filter(Model.equipment_type_id == t.id).distinct().all()
            mfr_list = []
            for mf in mfrs:
                models = db.query(Model).filter(Model.equipment_type_id == t.id, Model.manufacturer_id == mf.id).all()
                mfr_list.append({
                    "id": mf.id,
                    "name": mf.name,
                    "country": mf.country,
                    "website": mf.website,
                    "models": [{"id": mo.id, "model_name": mo.model_name, "series": mo.series} for mo in models]
                })
            type_list.append({
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "created_at": t.created_at,
                "updated_at": t.updated_at,
                "manufacturers": mfr_list,
                "subtypes": subtypes_list
            })
        tree.append({
            "id": m.id,
            "name": m.name,
            "description": m.description,
            "created_at": m.created_at,
            "updated_at": m.updated_at,
            "types": type_list
        })
    return tree

@router.get("/compressors")
def get_compressors_tree_compatibility(db: Session = Depends(get_db)):
    """[BACKWARD COMPATIBILITY] Flat Types list formerly used by the compressor-only frontend.
    Returns ALL equipment types across all masters (Pump, Compressor, Valve, etc.).
    Prefer /taxonomy/tree for new integrations as it includes the full Master->Type->Subtype hierarchy.
    """
    types = db.query(EquipmentType).all()
    tree = []
    for t in types:
        mfrs = db.query(Manufacturer).join(Model).filter(Model.equipment_type_id == t.id).distinct().all()
        mfr_list = []
        for mf in mfrs:
            models = db.query(Model).filter(Model.equipment_type_id == t.id, Model.manufacturer_id == mf.id).all()
            mfr_list.append({
                "id": mf.id,
                "name": mf.name,
                "country": mf.country,
                "website": mf.website,
                "models": [{"id": mo.id, "model_name": mo.model_name, "series": mo.series} for mo in models]
            })
        tree.append({
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "manufacturers": mfr_list
        })
    return tree
