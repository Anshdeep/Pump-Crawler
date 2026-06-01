import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Fallback database URL matches docker-compose services
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+psycopg://postgres:postgres_password@localhost:5432/compressors_db"
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dynamic vector support flag (checked at runtime / startup)
HAS_VECTOR_SUPPORT = False

try:
    with engine.connect() as _conn:
        _res = _conn.execute(text("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector');"))
        HAS_VECTOR_SUPPORT = _res.scalar()
except Exception:
    HAS_VECTOR_SUPPORT = False


def init_db():
    """Create pgvector extension, perform live table/column migrations, create tables, and seed defaults."""
    global HAS_VECTOR_SUPPORT
    from database.models import Base
    
    # 1. Try to enable pgvector extension
    try:
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        HAS_VECTOR_SUPPORT = True
        print("[OK] PostgreSQL pgvector extension is enabled!")
    except Exception as e:
        HAS_VECTOR_SUPPORT = False
        print("\n" + "="*80)
        print("[WARNING] The pgvector extension is not installed or available in PostgreSQL.")
        print("  -> The system will automatically fall back to pure-Python cosine similarity search.")
        print("  -> You do not need to compile pgvector now! The system is fully operational using safe fallbacks.")
        print("="*80 + "\n")

    # 2. Live migration checks
    try:
        with engine.begin() as conn:
            # Rename compressor_types to equipment_type
            res = conn.execute(text("SELECT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'compressor_types');"))
            if res.scalar():
                print("[Migration] Renaming table compressor_types -> equipment_type...")
                conn.execute(text("ALTER TABLE compressor_types RENAME TO equipment_type;"))
                
            # Rename compressor_subtypes to equipment_subtypes
            res = conn.execute(text("SELECT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'compressor_subtypes');"))
            if res.scalar():
                print("[Migration] Renaming table compressor_subtypes -> equipment_subtypes...")
                conn.execute(text("ALTER TABLE compressor_subtypes RENAME TO equipment_subtypes;"))
                
            # Rename type_id column in models to equipment_type_id
            res = conn.execute(text("SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='models' AND column_name='type_id');"))
            if res.scalar():
                print("[Migration] Renaming type_id column in models -> equipment_type_id...")
                conn.execute(text("ALTER TABLE models RENAME COLUMN type_id TO equipment_type_id;"))
                
            # Rename subtype_id column in models to equipment_subtype_id
            res = conn.execute(text("SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='models' AND column_name='subtype_id');"))
            if res.scalar():
                print("[Migration] Renaming subtype_id column in models -> equipment_subtype_id...")
                conn.execute(text("ALTER TABLE models RENAME COLUMN subtype_id TO equipment_subtype_id;"))

            # Alter existing tables to safely append flags if tables already exist
            conn.execute(text("ALTER TABLE manufacturers ADD COLUMN IF NOT EXISTS is_approved BOOLEAN DEFAULT FALSE;"))
            conn.execute(text("ALTER TABLE manufacturers ADD COLUMN IF NOT EXISTS is_harvested BOOLEAN DEFAULT FALSE;"))
            conn.execute(text("ALTER TABLE equipment_type ADD COLUMN IF NOT EXISTS equipment_master_id INTEGER;"))
            conn.execute(text("ALTER TABLE models ADD COLUMN IF NOT EXISTS equipment_master_id INTEGER;"))
            conn.execute(text("ALTER TABLE models ADD COLUMN IF NOT EXISTS is_approved BOOLEAN DEFAULT FALSE;"))
            conn.execute(text("ALTER TABLE models ADD COLUMN IF NOT EXISTS is_harvested BOOLEAN DEFAULT FALSE;"))

            # Safely append created_at and updated_at timestamp columns to core tables
            conn.execute(text("ALTER TABLE equipment_master ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;"))
            conn.execute(text("ALTER TABLE equipment_master ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;"))
            conn.execute(text("ALTER TABLE equipment_type ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;"))
            conn.execute(text("ALTER TABLE equipment_type ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;"))
            conn.execute(text("ALTER TABLE equipment_subtypes ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;"))
            conn.execute(text("ALTER TABLE equipment_subtypes ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;"))
            conn.execute(text("ALTER TABLE manufacturers ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;"))
            conn.execute(text("ALTER TABLE manufacturers ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;"))
            conn.execute(text("ALTER TABLE models ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;"))
            conn.execute(text("ALTER TABLE models ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;"))
    except Exception as e:
        print(f"[Migration Warning] Transient error during columns/tables migration: {e}")

    # 3. Create tables
    with engine.begin() as conn:
        Base.metadata.create_all(conn)

    # 4. Auto-seeding
    try:
        with engine.begin() as conn:
            # Seed equipment_master categories
            res = conn.execute(text("SELECT COUNT(*) FROM equipment_master;"))
            if res.scalar() == 0:
                print("[Seeding] Populating equipment_master defaults...")
                conn.execute(text(
                    "INSERT INTO equipment_master (name, description) VALUES "
                    "('Compressor', 'Industrial and process gas/air compressors'), "
                    "('Pump', 'Fluid transfer pump equipment'), "
                    "('Valve', 'Flow control valve systems');"
                ))
            
            # Map orphaned type / model rows to first master category (Compressor)
            res_comp = conn.execute(text("SELECT id FROM equipment_master WHERE name = 'Compressor';")).first()
            if res_comp:
                comp_id = res_comp[0]
                conn.execute(text("UPDATE equipment_type SET equipment_master_id = :comp_id WHERE equipment_master_id IS NULL;").bindparams(comp_id=comp_id))
                conn.execute(text("UPDATE models SET equipment_master_id = :comp_id WHERE equipment_master_id IS NULL;").bindparams(comp_id=comp_id))
                
            try:
                conn.execute(text("ALTER TABLE equipment_type ALTER COLUMN equipment_master_id SET NOT NULL;"))
            except Exception:
                pass

            # Seed equipment_type categories
            res_types = conn.execute(text("SELECT COUNT(*) FROM equipment_type;"))
            if res_types.scalar() == 0:
                print("[Seeding] Populating equipment_type defaults...")
                comp_id = conn.execute(text("SELECT id FROM equipment_master WHERE name = 'Compressor';")).scalar()
                pump_id = conn.execute(text("SELECT id FROM equipment_master WHERE name = 'Pump';")).scalar()
                
                if comp_id:
                    conn.execute(text(
                        "INSERT INTO equipment_type (equipment_master_id, name, description) VALUES "
                        "(:comp_id, 'Air Compressors', 'Air compression systems for tools and utility air'), "
                        "(:comp_id, 'Refrigeration Compressors', 'AC and low temperature thermal compression systems'), "
                        "(:comp_id, 'Gas Compressors', 'Natural gas and hydrocarbon process compression pipeline equipment'), "
                        "(:comp_id, 'Turbochargers/Superchargers', 'Automotive air induction systems'), "
                        "(:comp_id, 'Medical Compressors', 'Clean sterile compressed air for healthcare devices');"
                    ), {"comp_id": comp_id})
                    
                if pump_id:
                    conn.execute(text(
                        "INSERT INTO equipment_type (equipment_master_id, name, description) VALUES "
                        "(:pump_id, 'Centrifugal Pumps', 'High velocity fluid impeller transfer pumps'), "
                        "(:pump_id, 'Positive Displacement Pumps', 'Fixed volume mechanical displacement fluid pumps');"
                    ), {"pump_id": pump_id})

            # Seed equipment_subtypes
            res_sub = conn.execute(text("SELECT COUNT(*) FROM equipment_subtypes;"))
            if res_sub.scalar() == 0:
                print("[Seeding] Populating equipment_subtypes defaults...")
                types = conn.execute(text("SELECT id, name FROM equipment_type;")).all()
                type_map = {t[1]: t[0] for t in types}
                
                subtypes_data = {
                    "Air Compressors": ["Reciprocating", "Scroll", "Screw", "Centrifugal"],
                    "Refrigeration Compressors": ["Reciprocating", "Scroll", "Screw"],
                    "Gas Compressors": ["Reciprocating", "Centrifugal"],
                    "Turbochargers/Superchargers": ["Centrifugal", "Roots"],
                    "Medical Compressors": ["Oil-free diaphragm", "Scroll"],
                    "Centrifugal Pumps": ["Radial Flow", "Axial Flow", "Mixed Flow"],
                    "Positive Displacement Pumps": ["Reciprocating", "Rotary", "Diaphragm", "Screw", "Plunger"]
                }
                
                for type_name, subs in subtypes_data.items():
                    type_id = type_map.get(type_name)
                    if type_id:
                        for s_name in subs:
                            conn.execute(text(
                                "INSERT INTO equipment_subtypes (type_id, name) VALUES (:t_id, :name);"
                            ), {"t_id": type_id, "name": s_name})

            # Healing: Match existing models with null subtypes based on subtype name match in model_name or series
            print("[Healing] Retroactively matching existing models with null subtypes...")
            conn.execute(text("""
                UPDATE models m
                SET equipment_subtype_id = s.id
                FROM equipment_subtypes s
                WHERE m.equipment_subtype_id IS NULL
                  AND m.equipment_type_id = s.type_id
                  AND (
                    LOWER(m.model_name) LIKE '%' || LOWER(s.name) || '%'
                    OR (m.series IS NOT NULL AND LOWER(m.series) LIKE '%' || LOWER(s.name) || '%')
                  );
            """))

            # Seed dynamic settings defaults
            settings_defaults = [
                ("MAX_MANUFACTURERS_PER_TYPE", "3", "int", "Maximum number of manufacturers to discover per equipment type during Stage 1"),
                ("MAX_MODELS_PER_MANUFACTURER", "5", "int", "Maximum number of models to harvest per manufacturer during Stage 2"),
                ("REQUEST_DELAY_SECONDS", "4.0", "float", "Polite delay pause (in seconds) between scraped web pages to prevent rate limits"),
                ("CACHE_ENABLED", "true", "bool", "Enable file-system dynamic caching of scraped web HTML pages"),
                ("GEMINI_MODEL", "gemini-2.5-flash", "str", "Google Gemini GenAI model version to invoke for extraction"),
                ("RAG_SIMILARITY_THRESHOLD", "0.92", "float", "pgvector Cosine Similarity margin threshold for semantic deduplication (0.92 = 92% similarity)"),
            ]
            for key, value, vtype, desc in settings_defaults:
                res_set = conn.execute(text("SELECT COUNT(*) FROM system_settings WHERE key = :k;"), {"k": key})
                if res_set.scalar() == 0:
                    print(f"[Seeding] Adding system setting: {key} = {value}")
                    conn.execute(
                        text("INSERT INTO system_settings (key, value, value_type, description) VALUES (:k, :v, :t, :d);"),
                        {"k": key, "v": value, "t": vtype, "d": desc}
                    )
    except Exception as e:
        print(f"[Seeding Warning] Dynamic default seeding failed: {e}")

    print("[DB] Database and tables initialized successfully!")


def get_db():
    """FastAPI dependency to yield a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
