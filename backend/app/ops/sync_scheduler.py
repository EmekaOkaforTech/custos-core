import threading
import time
from datetime import datetime

from app.db import SessionLocal
from app.models.nas_sync_settings import NasSyncSettings
from app.ops.sync import run_sync


def _sync_loop():
    while True:
        db = SessionLocal()
        try:
            settings = db.query(NasSyncSettings).first()
            if settings and settings.enabled:
                result = run_sync(settings.mount_path)
                settings.last_sync_at = datetime.utcnow()
                settings.last_error = result.get("error")
                db.commit()
        finally:
            db.close()
        time.sleep(3600)


def start_sync_scheduler():
    thread = threading.Thread(target=_sync_loop, daemon=True)
    thread.start()
