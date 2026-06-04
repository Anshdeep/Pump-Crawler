import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database.connection as connection
from database.models import EquipmentMaster, EquipmentType

db = next(connection.get_db())
try:
    masters = db.query(EquipmentMaster).all()
    for m in masters:
        print(f"Master: {m.name} (ID: {m.id})")
        for t in m.types:
            print(f"  Type: {t.name} (ID: {t.id})")
finally:
    db.close()
