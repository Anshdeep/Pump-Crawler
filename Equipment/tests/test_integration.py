"""
tests/test_integration.py -- Automated Integration and Verification Suite (ASCII Compatible)
Located inside tests/ folder.
Tests:
  1. Schema migration, table registration, and taxonomy seeding.
  2. Taxonomy CRUD operations (Masters, Types, Subtypes).
  3. Dynamic Settings parsing and updating.
  4. Manufacturer profile creation and approvals.
  5. Model creation, RAG semantic deduplication, and model-level approvals.
"""

import os
import sys

# Add parent root folder to pythonpath so it can find database packages
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database.connection as connection
import database.crud as crud
from database.models import EquipmentMaster, EquipmentType, EquipmentSubtype, Manufacturer, Model, SystemSetting

def test_suite():
    print("\n" + "=" * 65)
    print("   Industrial Equipment Integration Test Suite")
    print("=" * 65 + "\n")

    # ── 1. Database Schema Initialization & Seeding ──
    print("[Test 1] Initializing database & running migrations...")
    try:
        connection.init_db()
        print("  [OK] DB schema and migrations loaded successfully!\n")
    except Exception as e:
        print(f"  [FAIL] DB Initialization failed: {e}")
        sys.exit(1)

    db = next(connection.get_db())

    try:
        # ── 2. Taxonomy CRUD Checks ──
        print("[Test 2] Testing Taxonomy CRUD...")
        # Get or create master category
        master = crud.get_or_create_equipment_master(db, name="Test Pump", description="Test Fluid pumps")
        assert master.id is not None, "Master category ID must not be None"
        print(f"  [OK] Equipment Master: '{master.name}' (ID: {master.id}) created.")

        # Get or create type
        etype = crud.get_or_create_equipment_type(db, name="Test Centrifugal", equipment_master_id=master.id, description="Fluid flow type")
        assert etype.id is not None, "Type ID must not be None"
        assert etype.equipment_master_id == master.id, "Type master relation mismatch"
        print(f"  [OK] Equipment Type: '{etype.name}' under '{master.name}' created.")

        # Get or create subtype
        subtype = crud.get_or_create_equipment_subtype(db, name="Test Submersible", type_id=etype.id)
        assert subtype.id is not None, "Subtype ID must not be None"
        assert subtype.type_id == etype.id, "Subtype type relation mismatch"
        print(f"  [OK] Equipment Subtype: '{subtype.name}' under '{etype.name}' created.\n")

        # ── 3. Dynamic Setting Configurations Checks ──
        print("[Test 3] Testing Dynamic Configuration Settings...")
        # Update setting
        crud.update_setting(db, "TEST_LIMIT", "12", "int")
        crud.update_setting(db, "TEST_ENABLED", "true", "bool")
        crud.update_setting(db, "TEST_PAUSE", "3.14", "float")

        # Check typed values
        limit_val = crud.get_setting_typed(db, "TEST_LIMIT", default=0)
        enabled_val = crud.get_setting_typed(db, "TEST_ENABLED", default=False)
        pause_val = crud.get_setting_typed(db, "TEST_PAUSE", default=0.0)

        assert limit_val == 12, f"Integer setting decode failed: {limit_val}"
        assert enabled_val is True, f"Boolean setting decode failed: {enabled_val}"
        assert abs(pause_val - 3.14) < 0.001, f"Float setting decode failed: {pause_val}"
        print("  [OK] Dynamic settings creation, type casting, and updates validated successfully!\n")

        # ── 4. Manufacturer Operations & approvals ──
        print("[Test 4] Testing Manufacturer Directory & Approvals...")
        mfr = crud.get_or_create_manufacturer(
            db, 
            name="Test Atlas Co", 
            country="Sweden", 
            website="testatlas.com", 
            description="Process manufacturer"
        )
        assert mfr.id is not None, "Manufacturer ID must not be None"
        assert mfr.is_approved is False, "Default manufacturer approval must be False"
        assert mfr.is_harvested is False, "Default manufacturer harvested must be False"

        # Toggle approval
        mfr.is_approved = True
        db.commit()
        db.refresh(mfr)
        assert mfr.is_approved is True, "Manufacturer approval update failed"
        print(f"  [OK] Manufacturer: '{mfr.name}' successfully verified & approved.\n")

        # ── 5. Model Operations, Approvals, & RAG Deduplication ──
        print("[Test 5] Testing Models & pgvector Cosine RAG matching...")
        # Create test models
        model1 = crud.create_equipment_model(
            db,
            equipment_master_id=master.id,
            equipment_type_id=etype.id,
            equipment_subtype_id=subtype.id,
            manufacturer_id=mfr.id,
            model_name="PUMP-500-X",
            series="X Series",
            product_url="http://testatlas.com/pump500",
            embedding=[0.1] * 768  # Mock 768 embedding
        )
        assert model1.id is not None, "Model ID must not be None"
        assert model1.is_approved is False, "Default model approval must be False"
        assert model1.is_harvested is False, "Default model harvested must be False"

        # Toggle model approval
        model1.is_approved = True
        db.commit()
        db.refresh(model1)
        assert model1.is_approved is True, "Model-level approval update failed"
        print(f"  [OK] Model: '{model1.model_name}' successfully verified & approved.")

        # Test exact match deduplication (Tier 1)
        match = crud.find_similar_model(
            db,
            equipment_type_id=etype.id,
            manufacturer_id=mfr.id,
            model_name="PUMP-500-X"
        )
        assert match is not None, "Exact match deduplication failed"
        assert match.id == model1.id, "Exact match returned wrong model"
        print("  [OK] RAG Tier 1 Name Deduplication verified successfully.")

        # Test vector match deduplication fallback (Tier 2)
        match_vector = crud.find_similar_model(
            db,
            equipment_type_id=etype.id,
            manufacturer_id=mfr.id,
            query_embedding=[0.1] * 768,  # Exact mock match
            distance_threshold=0.08
        )
        assert match_vector is not None, "Semantic match deduplication failed"
        assert match_vector.id == model1.id, "Semantic match returned wrong model"
        print("  [OK] RAG Tier 2 Semantic pgvector Deduplication verified successfully.\n")

        # Clean up test inputs to avoid database pollution
        print("[Cleanup] Removing test integration entries...")
        db.delete(model1)
        db.delete(mfr)
        db.delete(subtype)
        db.delete(etype)
        db.delete(master)
        
        # Clean settings
        db.query(SystemSetting).filter(SystemSetting.key.in_(["TEST_LIMIT", "TEST_ENABLED", "TEST_PAUSE"])).delete()
        db.commit()
        print("  [OK] Test suite records safely removed.")

    finally:
        db.close()

    print("\n" + "=" * 65)
    print("   ALL TESTS PASSED SUCCESSFULLY! PLATFORM INTEGRATION OK")
    print("=" * 65 + "\n")

if __name__ == "__main__":
    test_suite()
