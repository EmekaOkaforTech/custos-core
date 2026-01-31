import argparse
import os
import sys

try:
    import sqlcipher3
except Exception as exc:  # pragma: no cover
    print(f"sqlcipher3 import failed: {exc}")
    sys.exit(1)

DB_PATH_DEFAULT = "/srv/custos-core/backend/custos.db"


def get_key() -> str:
    key = os.getenv("CUSTOS_DATABASE_KEY", "")
    if not key:
        print("CUSTOS_DATABASE_KEY is not set.")
        sys.exit(2)
    return key


def open_conn(db_path: str):
    conn = sqlcipher3.connect(db_path)
    cur = conn.cursor()
    cur.execute(f"PRAGMA key='{get_key()}';")
    return conn, cur


def inspect_db(db_path: str) -> int:
    conn, cur = open_conn(db_path)
    try:
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables = [r[0] for r in cur.fetchall()]
        print("tables:", tables)
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version';")
        exists = cur.fetchone() is not None
        print("alembic_version exists:", exists)
        if exists:
            cur.execute("SELECT version_num FROM alembic_version;")
            print("alembic_version rows:", cur.fetchall())
        return 0
    finally:
        conn.close()


def stamp_head(db_path: str, head: str) -> int:
    conn, cur = open_conn(db_path)
    try:
        cur.execute(
            "CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY);"
        )
        cur.execute("DELETE FROM alembic_version;")
        cur.execute("INSERT INTO alembic_version (version_num) VALUES (?);", (head,))
        conn.commit()
        print(f"Stamped alembic_version to {head}")
        return 0
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect or repair alembic_version in SQLCipher DB.")
    parser.add_argument("command", choices=["inspect", "stamp"], help="Action to run")
    parser.add_argument("--db", default=DB_PATH_DEFAULT, help="Path to SQLCipher DB")
    parser.add_argument("--head", default="0007_relevant_at", help="Revision to stamp")
    args = parser.parse_args()

    if not os.path.exists(args.db):
        print(f"DB not found: {args.db}")
        return 3

    if args.command == "inspect":
        return inspect_db(args.db)
    return stamp_head(args.db, args.head)


if __name__ == "__main__":
    raise SystemExit(main())
