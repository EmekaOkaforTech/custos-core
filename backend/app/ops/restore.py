import json
import sys
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from shutil import copy2

from sqlalchemy import text

from app.db import create_db_engine
from app.ops.backup import BACKUP_VERSION, _write_status
from app.settings import get_db_path


def _checksum(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def restore_backup(backup_path: Path) -> dict:
    if not backup_path.exists():
        payload = {
            "status": "failed",
            "last_attempt": datetime.utcnow().isoformat(),
            "error": "backup_missing",
        }
        _write_status(payload)
        return payload

    meta_path = backup_path.with_suffix(".meta.json")
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if meta.get("version") != BACKUP_VERSION:
            payload = {
                "status": "failed",
                "last_attempt": datetime.utcnow().isoformat(),
                "error": "version_mismatch",
            }
            _write_status(payload)
            return payload

    checksum = _checksum(backup_path)
    db_path = Path(get_db_path())
    db_path.parent.mkdir(parents=True, exist_ok=True)
    copy2(backup_path, db_path)

    engine = create_db_engine()
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

    payload = {
        "status": "restored",
        "last_attempt": datetime.utcnow().isoformat(),
        "last_success": datetime.utcnow().isoformat(),
        "last_restore": datetime.utcnow().isoformat(),
        "path": str(backup_path),
        "checksum": checksum,
        "version": BACKUP_VERSION,
        "meta_path": str(meta_path),
    }
    _write_status(payload)
    return payload


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m app.ops.restore /path/to/backup.db")
        raise SystemExit(1)
    result = restore_backup(Path(sys.argv[1]))
    print(json.dumps(result, indent=2))
