import sys
import os

# Insert the 'Equipment' directory
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

import database.connection as connection
import database.crud as crud
from database.models import SystemSetting

db = next(connection.get_db())
try:
    settings = db.query(SystemSetting).all()
    for s in settings:
        print(f"Key: {s.key}, Value: {s.value}, ValueType: {s.value_type}")
finally:
    db.close()
