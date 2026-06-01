from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, func, ARRAY, Float, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, relationship
from database.connection import HAS_VECTOR_SUPPORT

# Choose the column type based on DB support
if HAS_VECTOR_SUPPORT:
    try:
        from pgvector.sqlalchemy import Vector
        EmbeddingType = Vector(768)
    except ImportError:
        EmbeddingType = ARRAY(Float)
else:
    EmbeddingType = ARRAY(Float)

Base = declarative_base()

class SystemSetting(Base):
    __tablename__ = "system_settings"

    key = Column(String(100), primary_key=True, index=True)
    value = Column(Text, nullable=False)
    value_type = Column(String(50), nullable=False, default="str")  # "int", "float", "bool", "str", "json"
    description = Column(Text, nullable=True)

class EquipmentMaster(Base):
    __tablename__ = "equipment_master"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    types = relationship("EquipmentType", back_populates="equipment_master", cascade="all, delete-orphan")
    models = relationship("Model", back_populates="equipment_master")

class EquipmentType(Base):
    __tablename__ = "equipment_type"

    id = Column(Integer, primary_key=True, index=True)
    equipment_master_id = Column(Integer, ForeignKey("equipment_master.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    equipment_master = relationship("EquipmentMaster", back_populates="types")
    subtypes = relationship("EquipmentSubtype", back_populates="equipment_type", cascade="all, delete-orphan")
    models = relationship("Model", back_populates="equipment_type")

class EquipmentSubtype(Base):
    __tablename__ = "equipment_subtypes"

    id = Column(Integer, primary_key=True, index=True)
    type_id = Column(Integer, ForeignKey("equipment_type.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    equipment_type = relationship("EquipmentType", back_populates="subtypes")
    models = relationship("Model", back_populates="subtype")

class Manufacturer(Base):
    __tablename__ = "manufacturers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    country = Column(String(100), nullable=True)
    website = Column(String(255), nullable=True)
    founded_year = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    is_approved = Column(Boolean, nullable=False, default=False)
    is_harvested = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    models = relationship("Model", back_populates="manufacturer", cascade="all, delete-orphan")

class Model(Base):
    __tablename__ = "models"

    id = Column(Integer, primary_key=True, index=True)
    equipment_master_id = Column(Integer, ForeignKey("equipment_master.id", ondelete="CASCADE"), nullable=True)
    equipment_type_id = Column(Integer, ForeignKey("equipment_type.id", ondelete="CASCADE"), nullable=False)
    equipment_subtype_id = Column(Integer, ForeignKey("equipment_subtypes.id", ondelete="SET NULL"), nullable=True)
    manufacturer_id = Column(Integer, ForeignKey("manufacturers.id", ondelete="CASCADE"), nullable=False)
    model_name = Column(String(150), nullable=False, index=True)
    series = Column(String(150), nullable=True)
    product_url = Column(Text, nullable=True)
    
    # Flags for approval workflow and indexing limits
    is_approved = Column(Boolean, nullable=False, default=False)
    is_harvested = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Gemini text-embedding-004 has 768 dimensions
    embedding = Column(EmbeddingType, nullable=True)

    equipment_master = relationship("EquipmentMaster", back_populates="models")
    equipment_type = relationship("EquipmentType", back_populates="models")
    subtype = relationship("EquipmentSubtype", back_populates="models")
    manufacturer = relationship("Manufacturer", back_populates="models")
    
    # 1-to-1 relationship with TechnicalAttribute
    technical_attributes = relationship("TechnicalAttribute", uselist=False, back_populates="model", cascade="all, delete-orphan")

class TechnicalAttribute(Base):
    __tablename__ = "technical_attributes"

    model_id = Column(Integer, ForeignKey("models.id", ondelete="CASCADE"), primary_key=True)
    attributes = Column(JSONB, nullable=False, default=dict)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    model = relationship("Model", back_populates="technical_attributes")

class CrawlHistory(Base):
    __tablename__ = "crawl_history"

    id = Column(Integer, primary_key=True, index=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), nullable=False) # "active", "completed", "failed"
    compressor_type = Column(String(100), nullable=True)  # Retain name for schema compatibility
    new_manufacturers_count = Column(Integer, default=0)
    new_models_count = Column(Integer, default=0)
    total_specs_enriched = Column(Integer, default=0)
    log_message = Column(Text, nullable=True)
