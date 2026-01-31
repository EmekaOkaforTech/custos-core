import threading
import time
from datetime import datetime
from uuid import uuid4

from app.db import SessionLocal
from app.models.inference_task import InferenceTask
from app.ops.accelerator import get_accelerator_status


POLL_INTERVAL_SECONDS = 10


def enqueue_task(task_type: str, payload: str | None, priority: int) -> InferenceTask:
    db = SessionLocal()
    try:
        task = InferenceTask(
            id="t_" + uuid4().hex,
            task_type=task_type,
            payload=payload,
            priority=priority,
            status="queued",
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return task
    finally:
        db.close()


def _next_task(db):
    return (
        db.query(InferenceTask)
        .filter(InferenceTask.status == "queued")
        .order_by(InferenceTask.priority.desc(), InferenceTask.created_at.asc())
        .first()
    )


def _process_task(db, task: InferenceTask) -> None:
    task.started_at = datetime.utcnow()
    status = get_accelerator_status()
    if status.status != "available" or status.throttled:
        task.status = "deferred"
        task.error = status.detail or "accelerator unavailable"
        task.completed_at = datetime.utcnow()
        db.commit()
        return

    # Placeholder for accelerator execution. Real inference is handled in future stories.
    task.status = "completed"
    task.completed_at = datetime.utcnow()
    task.error = None
    db.commit()


def run_once() -> dict:
    db = SessionLocal()
    try:
        task = _next_task(db)
        if not task:
            return {"processed": False}
        _process_task(db, task)
        return {"processed": True, "task_id": task.id, "status": task.status}
    finally:
        db.close()


def _loop():
    while True:
        try:
            run_once()
        except Exception:
            pass
        time.sleep(POLL_INTERVAL_SECONDS)


def start_inference_queue():
    thread = threading.Thread(target=_loop, daemon=True)
    thread.start()
