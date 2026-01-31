"""Background scheduler for NAS backups.

Epic 41: Home Network Architecture - Story 41.2
"""
from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta

from app.db import SessionLocal
from app.models.nas_backup_target import NasBackupTarget
from app.ops.backup import run_nas_backup


def _backup_loop():
    while True:
        try:
            db = SessionLocal()
            target = db.query(NasBackupTarget).first()
            if target and target.enabled and target.mount_path:
                last = target.last_backup_at
                stale = last is None or (datetime.utcnow() - last) >= timedelta(hours=24)
                if stale:
                    result = run_nas_backup(target.mount_path)
                    target.last_backup_at = datetime.utcnow()
                    target.last_error = result.get("nas", {}).get("error")
                    db.commit()
            db.close()
        except Exception:
            # best-effort scheduler; do not crash
            pass
        time.sleep(60 * 60)  # check hourly


def start_backup_scheduler():
    thread = threading.Thread(target=_backup_loop, daemon=True)
    thread.start()
    return thread
