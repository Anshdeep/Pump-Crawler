from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, func, ARRAY, Float
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

class CompressorType(Base):
    __tablename__ = "compressor_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)

    subtypes = relationship("CompressorSubtype", back_populates="compressor_type", cascade="all, delete-orphan")
    models = relationship("Model", back_populates="compressor_type")

class CompressorSubtype(Base):
    __tablename__ = "compressor_subtypes"

    id = Column(Integer, primary_key=True, index=True)
    type_id = Column(Integer, ForeignKey("compressor_types.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)

    compressor_type = relationship("CompressorType", back_populates="subtypes")
    models = relationship("Model", back_populates="subtype")

class Manufacturer(Base):
    __tablename__ = "manufacturers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    country = Column(String(100), nullable=True)
    website = Column(String(255), nullable=True)
    founded_year = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)

    models = relationship("Model", back_populates="manufacturer", cascade="all, delete-orphan")

class Model(Base):
    __tablename__ = "models"

    id = Column(Integer, primary_key=True, index=True)
    type_id = Column(Integer, ForeignKey("compressor_types.id", ondelete="CASCADE"), nullable=False)
    subtype_id = Column(Integer, ForeignKey("compressor_subtypes.id", ondelete="SET NULL"), nullable=True)
    manufacturer_id = Column(Integer, ForeignKey("manufacturers.id", ondelete="CASCADE"), nullable=False)
    model_name = Column(String(150), nullable=False, index=True)
    series = Column(String(150), nullable=True)
    product_url = Column(Text, nullable=True)
    
    # Gemini text-embedding-004 has 768 dimensions
    embedding = Column(EmbeddingType, nullable=True)

    compressor_type = relationship("CompressorType", back_populates="models")
    subtype = relationship("CompressorSubtype", back_populates="models")
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
    compressor_type = Column(String(100), nullable=True)
    new_manufacturers_count = Column(Integer, default=0)
    new_models_count = Column(Integer, default=0)
    total_specs_enriched = Column(Integer, default=0)
    log_message = Column(Text, nullable=True)
