import os
import sys
import hashlib

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


def normalize_payload(payload: str | None) -> str:
    if not payload:
        return ""
    return " ".join(payload.strip().split()).lower()


def make_key(meeting_id: str, capture_type: str, payload: str, people_ids: str | None, relevant_at: str | None) -> str:
    parts = [
        meeting_id,
        capture_type,
        payload,
        (people_ids or "").strip(),
        relevant_at or "",
    ]
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


conn = sqlcipher3.connect(DB_PATH)
cur = conn.cursor()
cur.execute(f"PRAGMA key='{KEY}';")

# Backfill ingestion_job.dedupe_key where NULL
cur.execute(
    """
    SELECT id, meeting_id, capture_type, payload, people_ids, relevant_at
    FROM ingestion_job
    WHERE dedupe_key IS NULL
    """
)
rows = cur.fetchall()
updated_jobs = 0
for jid, meeting_id, capture_type, payload, people_ids, relevant_at in rows:
    key = make_key(meeting_id, capture_type, normalize_payload(payload), people_ids, relevant_at)
    cur.execute("UPDATE ingestion_job SET dedupe_key = ? WHERE id = ?", (key, jid))
    updated_jobs += 1
print(f"Updated ingestion_job.dedupe_key for {updated_jobs} rows")

# Backfill source_record.dedupe_key by joining to ingestion_job when possible
cur.execute(
    """
    SELECT s.id, j.dedupe_key
    FROM source_record s
    JOIN ingestion_job j ON j.source_id = s.id
    WHERE s.dedupe_key IS NULL
    """
)
rows = cur.fetchall()
updated_sources = 0
for sid, dkey in rows:
    if dkey:
        cur.execute("UPDATE source_record SET dedupe_key = ? WHERE id = ?", (dkey, sid))
        updated_sources += 1
print(f"Updated source_record.dedupe_key for {updated_sources} rows")

conn.commit()
conn.close()
