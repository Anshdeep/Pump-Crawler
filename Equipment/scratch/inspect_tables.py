import sys, os
sys.path.insert(0, '.')
from database.connection import engine
from sqlalchemy import text

with engine.connect() as conn:
    # Get all table names in public schema
    res = conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public';"))
    tables = [row[0] for row in res]
    print("Tables:", tables)

    for table in tables:
        try:
            res_cols = conn.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_name='{table}';"))
            cols = [row[0] for row in res_cols]
            res_count = conn.execute(text(f"SELECT COUNT(*) FROM {table};"))
            cnt = res_count.scalar()
            print(f"Table {table}: {cnt} rows, columns: {cols}")
        except Exception as e:
            print(f"Error reading columns for {table}: {e}")
