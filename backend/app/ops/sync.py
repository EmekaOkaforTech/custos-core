from datetime import datetime
from pathlib import Path
from shutil import copy2

from app.settings import get_db_path


def run_sync(mount_path: str) -> dict:
    db_path = Path(get_db_path())
    target_dir = Path(mount_path)
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / "custos-sync.db"
    if not db_path.exists():
        return {"status": "failed", "error": "db_missing", "last_attempt": datetime.utcnow().isoformat()}
    copy2(db_path, target_path)
    return {
        "status": "succeeded",
        "last_attempt": datetime.utcnow().isoformat(),
        "last_success": datetime.utcnow().isoformat(),
        "path": str(target_path),
    }


def restore_from_sync(mount_path: str) -> dict:
    target_dir = Path(mount_path)
    sync_path = target_dir / "custos-sync.db"
    db_path = Path(get_db_path())
    if not sync_path.exists():
        return {"status": "failed", "error": "sync_missing", "last_attempt": datetime.utcnow().isoformat()}
    copy2(sync_path, db_path)
    return {
        "status": "succeeded",
        "last_attempt": datetime.utcnow().isoformat(),
        "path": str(sync_path),
    }
