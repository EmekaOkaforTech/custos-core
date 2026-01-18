import json
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from shutil import copy2

from app.settings import get_data_dir, get_db_path

STATUS_FILE = "backup_status.json"
BACKUP_VERSION = "1"


def _status_path() -> Path:
    return Path(get_data_dir()) / STATUS_FILE


def _write_status(payload: dict) -> None:
    data_dir = Path(get_data_dir())
    data_dir.mkdir(parents=True, exist_ok=True)
    with _status_path().open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def _checksum(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_backup() -> dict:
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    db_path = Path(get_db_path())
    backup_dir = Path(get_data_dir()) / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"backup-{timestamp}.db"
    meta_path = backup_dir / f"backup-{timestamp}.meta.json"

    if not db_path.exists():
        payload = {
            "status": "failed",
            "last_attempt": datetime.utcnow().isoformat(),
            "error": "db_missing",
        }
        _write_status(payload)
        return payload

    copy2(db_path, backup_path)
    checksum = _checksum(backup_path)
    meta = {
        "version": BACKUP_VERSION,
        "created_at": datetime.utcnow().isoformat(),
        "db_path": str(backup_path),
        "checksum": checksum,
    }
    with meta_path.open("w", encoding="utf-8") as handle:
        json.dump(meta, handle, indent=2)
    payload = {
        "status": "succeeded",
        "last_attempt": datetime.utcnow().isoformat(),
        "last_success": datetime.utcnow().isoformat(),
        "path": str(backup_path),
        "checksum": checksum,
        "version": BACKUP_VERSION,
        "meta_path": str(meta_path),
    }
    _write_status(payload)
    return payload


if __name__ == "__main__":
    result = create_backup()
    print(json.dumps(result, indent=2))
