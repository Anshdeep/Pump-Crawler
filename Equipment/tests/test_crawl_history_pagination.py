"""
tests/test_crawl_history_pagination.py -- Verification test for Crawl History pagination API
"""

import os
import sys

# Add parent root folder to pythonpath so it can find database packages
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from main import app
import database.connection as connection
from database.models import CrawlHistory
from datetime import datetime, timedelta

def test_crawl_history_pagination():
    print("\n" + "=" * 65)
    print("   Testing Crawl Run History Log Pagination API")
    print("=" * 65 + "\n")

    # 1. Initialize DB and TestClient
    connection.init_db()
    db = next(connection.get_db())
    client = TestClient(app)

    # 2. Seed mock crawl history runs
    print("[1/4] Seeding 15 mock CrawlHistory runs...")
    mock_runs = []
    base_time = datetime.utcnow()
    for i in range(15):
        run = CrawlHistory(
            started_at=base_time - timedelta(hours=i),
            completed_at=base_time - timedelta(hours=i) + timedelta(minutes=15),
            status="completed",
            target_category=f"Test Type {i % 3}",
            new_manufacturers_count=i,
            new_models_count=i * 2,
            total_specs_enriched=i * 5,
            log_message=f"Mock crawl history log entry number {i}"
        )
        db.add(run)
        mock_runs.append(run)
    db.commit()
    for run in mock_runs:
        db.refresh(run)
    
    print(f"  [OK] Successfully seeded {len(mock_runs)} mock runs in DB.\n")

    try:
        # 3. Request unpaginated history (backward compatibility)
        print("[2/4] Testing unpaginated /api/crawl/history (backward compatibility)...")
        res_unpaginated = client.get("/api/crawl/history")
        assert res_unpaginated.status_code == 200, "Unpaginated history request failed"
        data_unpaginated = res_unpaginated.json()
        assert isinstance(data_unpaginated, list), "Unpaginated response must be a list"
        assert len(data_unpaginated) >= 15, f"Expected at least 15 items, got {len(data_unpaginated)}"
        print("  [OK] Backward compatibility list response format verified!\n")

        # 4. Request paginated history
        print("[3/4] Testing paginated /api/crawl/history?page=1&limit=5...")
        res_paginated = client.get("/api/crawl/history", params={"page": 1, "limit": 5})
        assert res_paginated.status_code == 200, "Paginated history request failed"
        data_paginated = res_paginated.json()
        assert isinstance(data_paginated, dict), "Paginated response must be a dictionary"
        assert "total" in data_paginated, "Paginated response missing 'total'"
        assert "items" in data_paginated, "Paginated response missing 'items'"
        assert data_paginated["page"] == 1, f"Expected page 1, got {data_paginated['page']}"
        assert data_paginated["limit"] == 5, f"Expected limit 5, got {data_paginated['limit']}"
        assert len(data_paginated["items"]) == 5, f"Expected 5 items on page 1, got {len(data_paginated['items'])}"
        
        # Verify ordering (should be desc based on started_at)
        items = data_paginated["items"]
        for j in range(len(items) - 1):
            assert items[j]["started_at"] >= items[j+1]["started_at"], "Items are not properly ordered by started_at desc"

        # Check page 2
        print("  [OK] Page 1 elements and ordering correct.")
        print("  Testing paginated /api/crawl/history?page=2&limit=5...")
        res_page2 = client.get("/api/crawl/history", params={"page": 2, "limit": 5})
        assert res_page2.status_code == 200
        data_page2 = res_page2.json()
        assert len(data_page2["items"]) == 5
        assert data_page2["page"] == 2
        
        # Ensure items on page 2 are older than page 1 items
        assert data_page2["items"][0]["started_at"] <= items[-1]["started_at"], "Page 2 offset is incorrect"
        print("  [OK] Page 2 paging offset verified!\n")

    finally:
        # 5. Clean up seeded data
        print("[4/4] Cleaning up mock crawl records...")
        for run in mock_runs:
            db.delete(run)
        db.commit()
        db.close()
        print("  [OK] Database cleaned up successfully.")

    print("\n" + "=" * 65)
    print("   ALL PAGINATION API TESTS PASSED SUCCESSFULLY!")
    print("=" * 65 + "\n")

if __name__ == "__main__":
    test_crawl_history_pagination()
