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

# Create indexes if missing
cur.execute("PRAGMA index_list('ingestion_job');")
idx_names = {row[1] for row in cur.fetchall()}
if "ix_ingestion_job_dedupe_key" not in idx_names:
    cur.execute("CREATE UNIQUE INDEX ix_ingestion_job_dedupe_key ON ingestion_job(dedupe_key);")
    print("Created ix_ingestion_job_dedupe_key")
else:
    print("ix_ingestion_job_dedupe_key already exists")

cur.execute("PRAGMA index_list('source_record');")
idx_names = {row[1] for row in cur.fetchall()}
if "ix_source_record_dedupe_key" not in idx_names:
    cur.execute("CREATE UNIQUE INDEX ix_source_record_dedupe_key ON source_record(dedupe_key);")
    print("Created ix_source_record_dedupe_key")
else:
    print("ix_source_record_dedupe_key already exists")

# Stamp alembic_version to 0008
cur.execute("CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY);")
cur.execute("DELETE FROM alembic_version;")
cur.execute("INSERT INTO alembic_version (version_num) VALUES ('0008_dedupe_keys');")
print("Stamped alembic_version to 0008_dedupe_keys")

conn.commit()
conn.close()
