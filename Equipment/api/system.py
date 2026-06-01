from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.connection import get_db, init_db
from database.models import SystemSetting
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
