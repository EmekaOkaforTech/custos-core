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
    SELECT c.id, s.meeting_id, c.text, c.source_id
    FROM commitment c
    JOIN source_record s ON s.id = c.source_id
    ORDER BY s.meeting_id, c.text, c.created_at
    """
)
rows = cur.fetchall()
seen = set()
remove_ids = []
for cid, meeting_id, text, source_id in rows:
    key = (meeting_id, text.strip().lower())
    if key in seen:
        remove_ids.append((cid, source_id))
    else:
        seen.add(key)

if remove_ids:
    cur.executemany("DELETE FROM commitment WHERE id = ?", [(cid,) for cid, _ in remove_ids])
    conn.commit()
    print(f"Removed {len(remove_ids)} duplicate commitments")
else:
    print("No duplicate commitments found")

# Remove sources that no longer have commitments
cur.execute(
    """
    SELECT s.id
    FROM source_record s
    LEFT JOIN commitment c ON c.source_id = s.id
    WHERE c.id IS NULL
    """
)
orphan_ids = [row[0] for row in cur.fetchall()]
if orphan_ids:
    cur.executemany("DELETE FROM source_record WHERE id = ?", [(sid,) for sid in orphan_ids])
    conn.commit()
    print(f"Removed {len(orphan_ids)} orphan sources")

conn.close()
