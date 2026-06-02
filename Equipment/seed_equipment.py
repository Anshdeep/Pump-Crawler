import sys
import os
import json
sys.path.insert(0, '.')
from database.connection import init_db

def heal_placeholders():
    import config
    from database.connection import SessionLocal
    from database.models import Manufacturer, EquipmentType, Model
    
    mfr_json_path = config.MANUFACTURERS_JSON
    if not os.path.exists(mfr_json_path):
        print("[Healing] manufacturers.json output file not found. Skipping retroactive placeholders.")
        return
        
    try:
        with open(mfr_json_path, "r", encoding="utf-8") as f:
            mfrs_data = json.load(f)
    except Exception as e:
        print(f"[Healing Error] Failed to read manufacturers.json: {e}")
        return
        
    db = SessionLocal()
    try:
        count = 0
        for type_name, mfrs in mfrs_data.items():
            # Find equipment type
            etype = db.query(EquipmentType).filter(EquipmentType.name == type_name).first()
            if not etype:
                print(f"[Healing] Category type '{type_name}' not found in DB. Skipping.")
                continue
                
            for m in mfrs:
                mfr_name = m.get("name")
                if not mfr_name:
                    continue
                # Find manufacturer in DB
                mfr_obj = db.query(Manufacturer).filter(Manufacturer.name == mfr_name).first()
                if not mfr_obj:
                    continue
                    
                # Check if this manufacturer already has models (placeholder or real) under this type
                existing_model = db.query(Model).filter(
                    Model.manufacturer_id == mfr_obj.id,
                    Model.equipment_type_id == etype.id
                ).first()
                
                if not existing_model:
                    print(f"[Healing] Creating placeholder model for manufacturer '{mfr_name}' under type '{type_name}'")
                    placeholder = Model(
                        equipment_master_id=etype.equipment_master_id,
                        equipment_type_id=etype.id,
                        equipment_subtype_id=None,
                        manufacturer_id=mfr_obj.id,
                        model_name="TEMP_PLACEHOLDER",
                        series="Placeholder",
                        product_url=""
                    )
                    db.add(placeholder)
                    count += 1
        if count > 0:
            db.commit()
            print(f"[Healing] Successfully created {count} placeholder models to link manufacturers!")
        else:
            print("[Healing] No placeholders needed creation.")
    except Exception as e:
        db.rollback()
        print(f"[Healing Error] Exception during placeholder healing: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    print("=== Running Dynamic Equipment Taxonomy Seeder ===")
    init_db()
    print("=== Retroactive Placeholder Healing ===")
    heal_placeholders()
    print("=== Seeding completed successfully ===")
