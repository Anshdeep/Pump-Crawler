import sys
import os

# Add the project root to python path to ensure database imports work
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from database.connection import SessionLocal
from database.models import Model, TechnicalAttribute
from sqlalchemy.orm import Session

def deduplicate_database():
    print("=" * 60)
    print("[LOG] Running Database Deduplication & Clean-up Utility")
    print("=" * 60)

    db: Session = SessionLocal()
    try:
        # Fetch all models
        print("[1/4] Fetching all models from database...")
        models = db.query(Model).all()
        print(f"      Total model records in DB: {len(models)}")

        # Group models by (type_id, manufacturer_id, normalized_name)
        print("[2/4] Analyzing models for duplicates...")
        groups = {}
        for m in models:
            normalized_name = m.model_name.strip().lower()
            key = (m.type_id, m.manufacturer_id, normalized_name)
            groups.setdefault(key, []).append(m)

        duplicate_groups = {k: v for k, v in groups.items() if len(v) > 1}
        print(f"      Found {len(duplicate_groups)} distinct model groups with duplicates.")

        if not duplicate_groups:
            print("\n[SUCCESS] No duplicate models found! Your database is completely clean.")
            return

        total_merged = 0
        total_deleted = 0

        print("\n[3/4] Starting merging and deduplication process...")

        def score_model(m):
            # Sort score: (has_specs, has_vector, -m.id)
            # We prefer models with specs (technical attributes), then embeddings, then older models (smaller ID)
            has_specs = 1 if (m.technical_attributes and m.technical_attributes.attributes) else 0
            has_vector = 1 if (m.embedding is not None and len(m.embedding) > 0) else 0
            return (has_specs, has_vector, -m.id)

        for key, group in duplicate_groups.items():
            type_id, manufacturer_id, name = key
            
            # Sort candidates. First one is the best master record.
            sorted_candidates = sorted(group, key=score_model, reverse=True)
            master = sorted_candidates[0]
            redundants = sorted_candidates[1:]

            print(f"\n  * Group: Brand ID {manufacturer_id} | Type ID {type_id} | Name: '{master.model_name}'")
            print(f"    [*] Master Record selected: ID {master.id}")

            for m in redundants:
                print(f"    [-] Duplicate to delete: ID {m.id} ('{m.model_name}')")

                # 1. Merge technical attributes
                if m.technical_attributes and m.technical_attributes.attributes:
                    if not master.technical_attributes:
                        # Create new TechnicalAttribute linked to master
                        master.technical_attributes = TechnicalAttribute(
                            model_id=master.id,
                            attributes=m.technical_attributes.attributes
                        )
                        db.add(master.technical_attributes)
                        print(f"       -> Copied specs from ID {m.id} to Master ID {master.id}")
                    else:
                        # Merge dicts, master values overwrite/merge
                        merged_attrs = {**m.technical_attributes.attributes, **master.technical_attributes.attributes}
                        master.technical_attributes.attributes = merged_attrs
                        print(f"       -> Merged specs from ID {m.id} into Master ID {master.id}")

                # 2. Merge embedding if missing on master
                if (master.embedding is None or len(master.embedding) == 0) and (m.embedding is not None and len(m.embedding) > 0):
                    master.embedding = m.embedding
                    print(f"       -> Copied semantic embedding vector to Master")

                # 3. Merge metadata fields
                if not master.series and m.series:
                    master.series = m.series
                if not master.product_url and m.product_url:
                    master.product_url = m.product_url

                # 4. Remove duplicate model row (foreign keys cascade delete technical_attributes)
                db.delete(m)
                total_deleted += 1

            total_merged += 1

        print("\n[4/4] Saving changes to database...")
        db.commit()
        print(f"\n[SUCCESS] Successfully merged {total_merged} groups and deleted {total_deleted} duplicate models!")
        print("=" * 60)

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error during deduplication: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    deduplicate_database()
