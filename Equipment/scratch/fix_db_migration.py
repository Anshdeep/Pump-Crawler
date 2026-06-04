import sys, os
sys.path.insert(0, '.')
from database.connection import engine, init_db
from sqlalchemy import text

print("=== Starting Manual Database Migration Fix ===")

def run_migration():
    with engine.connect() as conn:
        # Check if old tables exist
        res = conn.execute(text("SELECT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'compressor_types');"))
        has_old_types = res.scalar()
        res = conn.execute(text("SELECT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'equipment_type');"))
        has_new_types = res.scalar()

        print(f"Old types exist: {has_old_types}, New types exist: {has_new_types}")

        # Drop the empty new tables if both exist, so we can rename the old ones
        if has_old_types and has_new_types:
            print("Both old and new tables exist. Dropping empty new tables to allow renaming...")
            # We use CASCADE to drop any constraints referring to them
            conn.execute(text("DROP TABLE IF EXISTS equipment_subtypes CASCADE;"))
            conn.execute(text("DROP TABLE IF EXISTS equipment_type CASCADE;"))
            # Commit/persist the drops
            conn.execute(text("COMMIT;"))

        # Now rename the old tables if they exist
        res = conn.execute(text("SELECT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'compressor_types');"))
        if res.scalar():
            print("Renaming compressor_types to equipment_type...")
            conn.execute(text("ALTER TABLE compressor_types RENAME TO equipment_type;"))
            conn.execute(text("COMMIT;"))

        res = conn.execute(text("SELECT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'compressor_subtypes');"))
        if res.scalar():
            print("Renaming compressor_subtypes to equipment_subtypes...")
            conn.execute(text("ALTER TABLE compressor_subtypes RENAME TO equipment_subtypes;"))
            conn.execute(text("COMMIT;"))

        # Rename type_id and subtype_id in models
        res = conn.execute(text("SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='models' AND column_name='type_id');"))
        if res.scalar():
            print("Renaming models.type_id to equipment_type_id...")
            conn.execute(text("ALTER TABLE models RENAME COLUMN type_id TO equipment_type_id;"))
            conn.execute(text("COMMIT;"))

        res = conn.execute(text("SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='models' AND column_name='subtype_id');"))
        if res.scalar():
            print("Renaming models.subtype_id to equipment_subtype_id...")
            conn.execute(text("ALTER TABLE models RENAME COLUMN subtype_id TO equipment_subtype_id;"))
            conn.execute(text("COMMIT;"))

        # Rename crawl_history.compressor_type to target_category
        res = conn.execute(text("SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='crawl_history' AND column_name='compressor_type');"))
        if res.scalar():
            print("Renaming crawl_history.compressor_type -> target_category...")
            conn.execute(text("ALTER TABLE crawl_history RENAME COLUMN compressor_type TO target_category;"))
            conn.execute(text("COMMIT;"))

        # Alter tables to add columns if they don't exist
        print("Adding columns to manufacturers table...")
        conn.execute(text("ALTER TABLE manufacturers ADD COLUMN IF NOT EXISTS is_approved BOOLEAN DEFAULT FALSE;"))
        conn.execute(text("ALTER TABLE manufacturers ADD COLUMN IF NOT EXISTS is_harvested BOOLEAN DEFAULT FALSE;"))
        conn.execute(text("ALTER TABLE manufacturers ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;"))
        conn.execute(text("ALTER TABLE manufacturers ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;"))
        conn.execute(text("COMMIT;"))

        print("Adding columns to models table...")
        conn.execute(text("ALTER TABLE models ADD COLUMN IF NOT EXISTS equipment_master_id INTEGER;"))
        conn.execute(text("ALTER TABLE models ADD COLUMN IF NOT EXISTS is_approved BOOLEAN DEFAULT FALSE;"))
        conn.execute(text("ALTER TABLE models ADD COLUMN IF NOT EXISTS is_harvested BOOLEAN DEFAULT FALSE;"))
        conn.execute(text("ALTER TABLE models ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;"))
        conn.execute(text("ALTER TABLE models ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;"))
        conn.execute(text("COMMIT;"))

        print("Adding columns to equipment_type table...")
        conn.execute(text("ALTER TABLE equipment_type ADD COLUMN IF NOT EXISTS equipment_master_id INTEGER;"))
        conn.execute(text("ALTER TABLE equipment_type ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;"))
        conn.execute(text("ALTER TABLE equipment_type ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;"))
        conn.execute(text("COMMIT;"))

        print("Adding columns to equipment_subtypes table...")
        conn.execute(text("ALTER TABLE equipment_subtypes ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;"))
        conn.execute(text("ALTER TABLE equipment_subtypes ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;"))
        conn.execute(text("COMMIT;"))

    print("Running database.connection.init_db() to create and seed remaining structures...")
    init_db()

    print("=== Database Migration Fix Completed Successfully! ===")

if __name__ == "__main__":
    run_migration()
