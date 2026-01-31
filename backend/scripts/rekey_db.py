import os
import sys

try:
    import sqlcipher3
except Exception as exc:
    print(f"sqlcipher3 import failed: {exc}")
    sys.exit(1)

DB_PATH = os.getenv("CUSTOS_DB_PATH", "/srv/custos-core/backend/custos.db")
OLD_KEY = os.getenv("CUSTOS_DATABASE_KEY", "")
NEW_KEY = os.getenv("NEW_CUSTOS_DATABASE_KEY", "")

if not OLD_KEY:
    print("CUSTOS_DATABASE_KEY is not set.")
    sys.exit(2)
if not NEW_KEY:
    print("NEW_CUSTOS_DATABASE_KEY is not set.")
    sys.exit(3)

conn = sqlcipher3.connect(DB_PATH)
cur = conn.cursor()
cur.execute(f"PRAGMA key='{OLD_KEY}';")
cur.execute("PRAGMA cipher_version;")
cur.execute(f"PRAGMA rekey='{NEW_KEY}';")
conn.commit()
conn.close()
print("Rekey complete")
