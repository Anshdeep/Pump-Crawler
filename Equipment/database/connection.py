import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Fallback database URL matches docker-compose services
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+psycopg://postgres:postgres_password@localhost:5432/equipment_db"
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


def get_master_name_from_filename(filename: str) -> str:
    import os
    name = os.path.splitext(os.path.basename(filename))[0].lower()
    if name.endswith("ies"):
        name = name[:-3] + "y"
    elif name.endswith("es"):
        if name.endswith("valves"):
            name = "valve"
        else:
            name = name[:-2]
    elif name.endswith("s"):
        name = name[:-1]
    return name.capitalize()


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

            # Rename crawl_history.compressor_type -> target_category (equipment-agnostic field)
            res = conn.execute(text("SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='crawl_history' AND column_name='compressor_type');"))
            if res.scalar():
                print("[Migration] Renaming crawl_history.compressor_type -> target_category...")
                conn.execute(text("ALTER TABLE crawl_history RENAME COLUMN compressor_type TO target_category;"))

            # Ensure target_category column exists (for DBs that never had compressor_type)
            conn.execute(text("ALTER TABLE crawl_history ADD COLUMN IF NOT EXISTS target_category VARCHAR(100);"))
                
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
            
            # Map orphaned type / model rows to the first available master category
            # (historically Compressor, but any master is fine as a fallback)
            res_first_master = conn.execute(text("SELECT id FROM equipment_master ORDER BY id ASC LIMIT 1;")).first()
            if res_first_master:
                first_master_id = res_first_master[0]
                conn.execute(text("UPDATE equipment_type SET equipment_master_id = :m_id WHERE equipment_master_id IS NULL;").bindparams(m_id=first_master_id))
                conn.execute(text("UPDATE models SET equipment_master_id = :m_id WHERE equipment_master_id IS NULL;").bindparams(m_id=first_master_id))
                
            try:
                conn.execute(text("ALTER TABLE equipment_type ALTER COLUMN equipment_master_id SET NOT NULL;"))
            except Exception:
                pass

            # Dynamic Seeding from json configuration files in DATA_DIR
            import glob
            import config
            import json
            
            data_dir = getattr(config, "DATA_DIR", os.path.join(config.BASE_DIR, "data"))
            json_files = glob.glob(os.path.join(data_dir, "*.json"))
            
            for jf in json_files:
                filename = os.path.basename(jf)
                if filename in ["manufacturers.json", "models.json", "equipment_data.json", "compressors_data.json"]:
                    continue
                    
                master_name = get_master_name_from_filename(filename)
                
                # Check or insert master category
                res_m = conn.execute(
                    text("SELECT id FROM equipment_master WHERE name = :name;"),
                    {"name": master_name}
                ).first()
                if not res_m:
                    print(f"[Seeding] Adding equipment_master: {master_name}")
                    conn.execute(
                        text("INSERT INTO equipment_master (name, description) VALUES (:name, :desc);"),
                        {"name": master_name, "desc": f"{master_name} equipment catalog"}
                    )
                    master_id = conn.execute(
                        text("SELECT id FROM equipment_master WHERE name = :name;"),
                        {"name": master_name}
                    ).scalar()
                else:
                    master_id = res_m[0]
                    
                try:
                    with open(jf, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                        if not content:
                            continue
                        equip_types = json.loads(content)
                except Exception as e:
                    print(f"[Seeding Warning] Failed to parse {filename}: {e}")
                    continue
                    
                if not isinstance(equip_types, list):
                    continue
                    
                for item in equip_types:
                    t_name = item.get("type")
                    if not t_name:
                        continue
                    subtypes = item.get("subtypes", [])
                    apps = item.get("applications", [])
                    t_desc = f"Applications: {', '.join(apps)}" if apps else f"{t_name} equipment"
                    
                    # Check or insert equipment type under the resolved master category
                    res_t = conn.execute(
                        text("SELECT id FROM equipment_type WHERE name = :name AND equipment_master_id = :master_id;"),
                        {"name": t_name, "master_id": master_id}
                    ).first()
                    if not res_t:
                        print(f"[Seeding] Adding equipment_type: {t_name} under {master_name}")
                        conn.execute(
                            text("INSERT INTO equipment_type (equipment_master_id, name, description) VALUES (:master_id, :name, :desc);"),
                            {"master_id": master_id, "name": t_name, "desc": t_desc}
                        )
                        type_id = conn.execute(
                            text("SELECT id FROM equipment_type WHERE name = :name AND equipment_master_id = :master_id;"),
                            {"name": t_name, "master_id": master_id}
                        ).scalar()
                    else:
                        type_id = res_t[0]
                        conn.execute(
                            text("UPDATE equipment_type SET description = :desc WHERE id = :id;"),
                            {"desc": t_desc, "id": type_id}
                        )
                        
                    # Sync subtypes: delete obsolete ones no longer in the json configuration
                    existing_subs = conn.execute(
                        text("SELECT id, name FROM equipment_subtypes WHERE type_id = :type_id;"),
                        {"type_id": type_id}
                    ).all()
                    for row in existing_subs:
                        sub_id, sub_name = row[0], row[1]
                        if sub_name not in subtypes:
                            print(f"[Seeding] Deleting obsolete equipment_subtype: {sub_name} (ID: {sub_id}) under type {t_name}")
                            conn.execute(
                                text("DELETE FROM equipment_subtypes WHERE id = :sub_id;"),
                                {"sub_id": sub_id}
                            )

                    # Check or insert subtypes
                    for s_name in subtypes:
                        res_s = conn.execute(
                            text("SELECT id FROM equipment_subtypes WHERE type_id = :type_id AND name = :name;"),
                            {"type_id": type_id, "name": s_name}
                        ).first()
                        if not res_s:
                            print(f"[Seeding] Adding equipment_subtype: {s_name} under {t_name}")
                            conn.execute(
                                text("INSERT INTO equipment_subtypes (type_id, name) VALUES (:type_id, :name);"),
                                {"type_id": type_id, "name": s_name}
                            )

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
