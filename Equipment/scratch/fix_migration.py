"""One-off migration: add target_category column to crawl_history if missing."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import engine
from sqlalchemy import text

with engine.begin() as conn:
    conn.execute(text(
        "ALTER TABLE crawl_history ADD COLUMN IF NOT EXISTS target_category VARCHAR(100);"
    ))
    result = conn.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name='crawl_history' ORDER BY ordinal_position;"
    ))
    cols = [row[0] for row in result]
    print("crawl_history columns:", cols)

if "target_category" in cols:
    print("[OK] target_category column is now present. Restart the server.")
else:
    print("[FAIL] Column still missing - check DB permissions.")
