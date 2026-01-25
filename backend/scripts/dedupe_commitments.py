import os
import sys

try:
    import sqlcipher3
except Exception as exc:
    print(f"sqlcipher3 import failed: {exc}")
    sys.exit(1)

DB_PATH = os.getenv("CUSTOS_DB_PATH", "/srv/custos-core/backend/custos.db")
KEY = os.getenv("CUSTOS_DATABASE_KEY", "")
if not KEY:
    print("CUSTOS_DATABASE_KEY is not set.")
    sys.exit(2)

conn = sqlcipher3.connect(DB_PATH)
cur = conn.cursor()
cur.execute(f"PRAGMA key='{KEY}';")

cur.execute(
    """
    SELECT c.id, c.source_id, c.text
    FROM commitment c
    ORDER BY c.source_id, c.text, c.created_at
    """
)
rows = cur.fetchall()
seen = set()
remove_ids = []
for cid, source_id, text in rows:
    key = (source_id, text.strip().lower())
    if key in seen:
        remove_ids.append(cid)
    else:
        seen.add(key)

if remove_ids:
    cur.executemany("DELETE FROM commitment WHERE id = ?", [(cid,) for cid in remove_ids])
    conn.commit()
    print(f"Removed {len(remove_ids)} duplicate commitments")
else:
    print("No duplicate commitments found")

conn.close()
