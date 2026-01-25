import os
import sys
from datetime import datetime
from uuid import uuid4

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
    SELECT j.id, j.meeting_id, j.capture_type, j.relevant_at, j.created_at, j.completed_at, j.dedupe_key, j.source_id
    FROM ingestion_job j
    WHERE j.source_id IS NOT NULL
      AND j.source_id NOT IN (SELECT id FROM source_record)
    ORDER BY j.created_at ASC
    """
)
missing = cur.fetchall()

created = 0
relinked = 0
for job_id, meeting_id, capture_type, relevant_at, created_at, completed_at, dedupe_key, source_id in missing:
    # If a source with same dedupe_key exists, relink job instead of creating a duplicate.
    if dedupe_key:
        cur.execute("SELECT id FROM source_record WHERE dedupe_key = ?", (dedupe_key,))
        row = cur.fetchone()
        if row:
            cur.execute("UPDATE ingestion_job SET source_id = ? WHERE id = ?", (row[0], job_id))
            relinked += 1
            continue

    new_source_id = source_id or f"s_{uuid4().hex}"
    captured_at = completed_at or created_at or datetime.utcnow().isoformat()
    cur.execute(
        """
        INSERT INTO source_record (id, meeting_id, captured_at, capture_type, uri, relevant_at, dedupe_key)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            new_source_id,
            meeting_id,
            captured_at,
            capture_type,
            f"local://sources/{new_source_id}",
            relevant_at,
            dedupe_key,
        ),
    )
    cur.execute("UPDATE ingestion_job SET source_id = ? WHERE id = ?", (new_source_id, job_id))
    created += 1

conn.commit()
print({"missing_jobs": len(missing), "sources_created": created, "jobs_relinked": relinked})
conn.close()
