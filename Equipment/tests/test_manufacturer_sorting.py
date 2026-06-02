"""
tests/test_manufacturer_sorting.py -- Verification test for Manufacturer Directory sorting API
"""

import os
import sys

# Add parent root folder to pythonpath so it can find database packages
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from main import app
import database.connection as connection
from database.models import Manufacturer, Model
from datetime import datetime, timedelta

def test_manufacturer_sorting():
    print("\n" + "=" * 65)
    print("   Testing Manufacturer Directory Column Sorting API")
    print("=" * 65 + "\n")

    # 1. Initialize DB and TestClient
    connection.init_db()
    db = next(connection.get_db())
    client = TestClient(app)

    # 2. Seed mock manufacturers
    print("[1/5] Seeding mock manufacturers for sorting check...")
    mfr_a = Manufacturer(
        name="Apex Industrial",
        country="USA",
        website="apexind.com",
        founded_year=1990,
        description="High precision manufacturer",
        is_approved=True,
        is_harvested=True
    )
    mfr_b = Manufacturer(
        name="Zenith Fluid",
        country="Germany",
        website="zenithfluid.de",
        founded_year=1950,
        description="Pumps and accessories",
        is_approved=False,
        is_harvested=False
    )
    mfr_c = Manufacturer(
        name="Century Systems",
        country="Japan",
        website="centurytech.jp",
        founded_year=2010,
        description="Automation parts",
        is_approved=True,
        is_harvested=False
    )
    
    db.add_all([mfr_a, mfr_b, mfr_c])
    db.commit()
    db.refresh(mfr_a)
    db.refresh(mfr_b)
    db.refresh(mfr_c)
    
    # Add a mock model to mfr_a to test model count sorting
    model = Model(
        equipment_master_id=1,  # Mock
        equipment_type_id=1,    # Mock
        manufacturer_id=mfr_a.id,
        model_name="MOCK-MODEL-1",
        series="A Series"
    )
    db.add(model)
    db.commit()
    db.refresh(model)

    print("  [OK] Mock manufacturers and model successfully seeded.\n")

    try:
        # 3. Test sort by Name ascending/descending
        print("[2/5] Testing sorting by Name...")
        res_asc = client.get("/api/manufacturers", params={"sort_by": "name", "sort_desc": False, "page": 1, "limit": 100})
        names_asc = [m["name"] for m in res_asc.json()["items"] if m["name"] in ["Apex Industrial", "Zenith Fluid", "Century Systems"]]
        assert names_asc == ["Apex Industrial", "Century Systems", "Zenith Fluid"], f"Expected Apex, Century, Zenith, got {names_asc}"
        
        res_desc = client.get("/api/manufacturers", params={"sort_by": "name", "sort_desc": True, "page": 1, "limit": 100})
        names_desc = [m["name"] for m in res_desc.json()["items"] if m["name"] in ["Apex Industrial", "Zenith Fluid", "Century Systems"]]
        assert names_desc == ["Zenith Fluid", "Century Systems", "Apex Industrial"], f"Expected Zenith, Century, Apex, got {names_desc}"
        print("  [OK] Name sorting verified successfully!\n")

        # 4. Test sort by HQ Country
        print("[3/5] Testing sorting by HQ Country...")
        res_country_asc = client.get("/api/manufacturers", params={"sort_by": "country", "sort_desc": False, "page": 1, "limit": 100})
        countries_asc = [m["country"] for m in res_country_asc.json()["items"] if m["name"] in ["Apex Industrial", "Zenith Fluid", "Century Systems"]]
        assert countries_asc == ["Germany", "Japan", "USA"], f"Expected Germany, Japan, USA, got {countries_asc}"
        print("  [OK] HQ Country sorting verified successfully!\n")

        # 5. Test sort by Model Count
        print("[4/5] Testing sorting by Model Count...")
        res_model_desc = client.get("/api/manufacturers", params={"sort_by": "model_count", "sort_desc": True, "page": 1, "limit": 100})
        # Apex has 1 model, others have 0.
        # Find index of Apex, Zenith, Century
        names = [m["name"] for m in res_model_desc.json()["items"] if m["name"] in ["Apex Industrial", "Zenith Fluid", "Century Systems"]]
        assert names[0] == "Apex Industrial", f"Apex Industrial must appear first among the three, got {names}"
        print("  [OK] Model Count sorting verified successfully!\n")

    finally:
        # Cleanup
        print("[5/5] Cleaning up seeded mock records...")
        db.delete(model)
        db.delete(mfr_a)
        db.delete(mfr_b)
        db.delete(mfr_c)
        db.commit()
        db.close()
        print("  [OK] Database cleaned up successfully.")

    print("\n" + "=" * 65)
    print("   ALL MANUFACTURER SORTING TESTS PASSED SUCCESSFULLY!")
    print("=" * 65 + "\n")

if __name__ == "__main__":
    test_manufacturer_sorting()
