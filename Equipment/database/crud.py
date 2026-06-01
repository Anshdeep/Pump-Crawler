from sqlalchemy.orm import Session
from sqlalchemy import text, func
from database.models import (
    SystemSetting, EquipmentMaster, EquipmentType, EquipmentSubtype,
    Manufacturer, Model, TechnicalAttribute
)

# ── Dynamic System Settings Helper Repository ────────────────────────────────

def get_setting(db: Session, key: str, default: str = None) -> str:
    obj = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    return obj.value if obj else default

def get_setting_typed(db: Session, key: str, default = None):
    obj = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if not obj:
        return default
    val = obj.value
    vtype = obj.value_type
    if vtype == "int":
        try:
            return int(val)
        except ValueError:
            return default
    elif vtype == "float":
        try:
            return float(val)
        except ValueError:
            return default
    elif vtype == "bool":
        return val.strip().lower() in ["true", "1", "yes", "on"]
    return val

def update_setting(db: Session, key: str, value: str, value_type: str = "str") -> SystemSetting:
    obj = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if not obj:
        obj = SystemSetting(key=key, value=str(value), value_type=value_type)
        db.add(obj)
    else:
        obj.value = str(value)
        if value_type != "str":
            obj.value_type = value_type
    db.commit()
    db.refresh(obj)
    return obj

# ── Taxonomy Hierarchy Repository ───────────────────────────────────────────

def get_or_create_equipment_master(db: Session, name: str, description: str = None) -> EquipmentMaster:
    obj = db.query(EquipmentMaster).filter(EquipmentMaster.name.ilike(name)).first()
    if not obj:
        obj = EquipmentMaster(name=name, description=description)
        db.add(obj)
        db.commit()
        db.refresh(obj)
    return obj

def get_or_create_equipment_type(db: Session, name: str, equipment_master_id: int, description: str = None) -> EquipmentType:
    obj = db.query(EquipmentType).filter(
        EquipmentType.name.ilike(name),
        EquipmentType.equipment_master_id == equipment_master_id
    ).first()
    if not obj:
        obj = EquipmentType(name=name, equipment_master_id=equipment_master_id, description=description)
        db.add(obj)
        db.commit()
        db.refresh(obj)
    return obj

def get_or_create_equipment_subtype(db: Session, name: str, type_id: int) -> EquipmentSubtype:
    obj = db.query(EquipmentSubtype).filter(
        EquipmentSubtype.name.ilike(name),
        EquipmentSubtype.type_id == type_id
    ).first()
    if not obj:
        obj = EquipmentSubtype(name=name, type_id=type_id)
        db.add(obj)
        db.commit()
        db.refresh(obj)
    return obj

# ── Manufacturer & Model Repository ──────────────────────────────────────────

def get_or_create_manufacturer(
    db: Session, 
    name: str, 
    country: str = None, 
    website: str = None, 
    description: str = None
) -> Manufacturer:
    obj = db.query(Manufacturer).filter(Manufacturer.name.ilike(name)).first()
    if not obj:
        obj = Manufacturer(
            name=name,
            country=country,
            website=website,
            description=description
        )
        db.add(obj)
        db.commit()
        db.refresh(obj)
    else:
        updated = False
        if country and not obj.country:
            obj.country = country
            updated = True
        if website and not obj.website:
            obj.website = website
            updated = True
        if description and not obj.description:
            obj.description = description
            updated = True
        if updated:
            db.commit()
            db.refresh(obj)
    return obj

def create_equipment_model(
    db: Session,
    equipment_master_id: int,
    equipment_type_id: int,
    equipment_subtype_id: int | None,
    manufacturer_id: int,
    model_name: str,
    series: str = None,
    product_url: str = None,
    embedding: list[float] = None
) -> Model:
    obj = Model(
        equipment_master_id=equipment_master_id,
        equipment_type_id=equipment_type_id,
        equipment_subtype_id=equipment_subtype_id,
        manufacturer_id=manufacturer_id,
        model_name=model_name,
        series=series,
        product_url=product_url,
        embedding=embedding,
        is_approved=False,
        is_harvested=False
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

def save_technical_attributes(db: Session, model_id: int, attributes: dict) -> TechnicalAttribute:
    obj = db.query(TechnicalAttribute).filter(TechnicalAttribute.model_id == model_id).first()
    if not obj:
        obj = TechnicalAttribute(model_id=model_id, attributes=attributes)
        db.add(obj)
    else:
        obj.attributes = attributes
    db.commit()
    db.refresh(obj)
    return obj

# ── pgvector Cosine RAG Semantic Deduplication ──────────────────────────────

def find_similar_model(
    db: Session,
    equipment_type_id: int,
    manufacturer_id: int,
    query_embedding: list[float] | None = None,
    distance_threshold: float = 0.08,  # Default Cosine Distance <= 0.08 means Similarity >= 0.92
    model_name: str | None = None
) -> Model | None:
    """
    Search by exact name match (Tier 1) or pgvector embedding column similarity (Tier 2)
    to find similar model under the same category & manufacturer.
    If database does not support pgvector, falls back to a pure-Python cosine similarity search.
    Returns Model object if a match is found, else None.
    """
    # Tier 1 (Exact Match): Case-insensitive, whitespace-trimmed name check
    if model_name:
        trimmed_name = model_name.strip()
        exact_match = db.query(Model).filter(
            Model.equipment_type_id == equipment_type_id,
            Model.manufacturer_id == manufacturer_id,
            func.lower(func.trim(Model.model_name)) == func.lower(trimmed_name)
        ).first()
        if exact_match:
            print(f"  [Exact Match] Found model with identical name '{exact_match.model_name}'")
            return exact_match

    # Tier 2 (Vector Semantic Match)
    if not query_embedding:
        return None
        
    from database.connection import HAS_VECTOR_SUPPORT
    
    if HAS_VECTOR_SUPPORT:
        # Get the nearest neighbor by cosine distance and fetch computed distance directly
        result = db.query(
            Model,
            Model.embedding.cosine_distance(query_embedding).label("distance")
        ).filter(
            Model.equipment_type_id == equipment_type_id,
            Model.manufacturer_id == manufacturer_id,
            Model.embedding.isnot(None)
        ).order_by(
            Model.embedding.cosine_distance(query_embedding)
        ).first()
        
        if result:
            nearest_model, distance = result
            if distance is not None and distance <= distance_threshold:
                print(f"  [RAG Semantic Match] Found similar model '{nearest_model.model_name}' (distance: {distance:.4f})")
                return nearest_model
    else:
        # Pure Python fallback using cosine similarity
        import math
        
        def cosine_distance(v1, v2):
            if not v1 or not v2 or len(v1) != len(v2):
                return 1.0
            dot_product = sum(a * b for a, b in zip(v1, v2))
            magnitude_v1 = math.sqrt(sum(a * a for a in v1))
            magnitude_v2 = math.sqrt(sum(b * b for b in v2))
            if magnitude_v1 == 0 or magnitude_v2 == 0:
                return 1.0
            similarity = dot_product / (magnitude_v1 * magnitude_v2)
            return 1.0 - similarity

        # Fetch candidate models under the same category & manufacturer
        candidates = db.query(Model).filter(
            Model.equipment_type_id == equipment_type_id,
            Model.manufacturer_id == manufacturer_id,
            Model.embedding.isnot(None)
        ).all()
        
        best_model = None
        min_distance = 1.0
        
        for candidate in candidates:
            dist = cosine_distance(candidate.embedding, query_embedding)
            if dist < min_distance:
                min_distance = dist
                best_model = candidate
                
        if best_model and min_distance <= distance_threshold:
            print(f"  [Python RAG Semantic Fallback] Found similar model '{best_model.model_name}' (distance: {min_distance:.4f})")
            return best_model
            
    return None
