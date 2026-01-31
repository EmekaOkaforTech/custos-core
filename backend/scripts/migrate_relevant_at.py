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

# Ensure ingestion_job.relevant_at
cur.execute("PRAGMA table_info(ingestion_job);")
cols = {row[1] for row in cur.fetchall()}
if "relevant_at" not in cols:
    cur.execute("ALTER TABLE ingestion_job ADD COLUMN relevant_at DATETIME;")
    print("Added ingestion_job.relevant_at")
else:
    print("ingestion_job.relevant_at already exists")

# Ensure source_record.relevant_at
cur.execute("PRAGMA table_info(source_record);")
cols = {row[1] for row in cur.fetchall()}
if "relevant_at" not in cols:
    cur.execute("ALTER TABLE source_record ADD COLUMN relevant_at DATETIME;")
    print("Added source_record.relevant_at")
else:
    print("source_record.relevant_at already exists")

# Ensure alembic_version row
cur.execute("CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY);")
cur.execute("DELETE FROM alembic_version;")
cur.execute("INSERT INTO alembic_version (version_num) VALUES ('0007_relevant_at');")
print("Stamped alembic_version to 0007_relevant_at")

conn.commit()
conn.close()
