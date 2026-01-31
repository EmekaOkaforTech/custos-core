import threading
import time
from datetime import datetime
from uuid import uuid4
import json
import httpx

from app.db import SessionLocal
from app.models.inference_task import InferenceTask
from app.models.ingestion_job import IngestionJob
from app.models.network_settings import NetworkSettings
from app.models.source_record import SourceRecord
from app.ops.whisper_hailo import transcribe_audio
from app.ops.summarization import summarize_text
from app.ops.accelerator import get_accelerator_status


POLL_INTERVAL_SECONDS = 10


def _get_inference_settings(db):
    settings = db.query(NetworkSettings).first()
    return settings


def _delegate_to_server(url: str, media_path: str) -> tuple[str | None, str | None]:
    if not url or not media_path:
        return None, "inference_server_unavailable"
    try:
        with open(media_path, "rb") as handle:
            files = {"file": ("audio.webm", handle, "audio/webm")}
            response = httpx.post(f"{url.rstrip('/')}/whisper", files=files, timeout=60)
        if response.status_code != 200:
            return None, f"inference_server_error:{response.status_code}"
        payload = response.json()
        text_out = payload.get("text") if isinstance(payload, dict) else None
        return text_out, None
    except Exception as exc:
        return None, f"inference_server_error:{exc}"


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
    if task.task_type not in {"whisper_transcribe", "summarize"} and (status.status != "available" or status.throttled):
        task.status = "deferred"
        task.error = status.detail or "accelerator unavailable"
        task.completed_at = datetime.utcnow()
        db.commit()
        return

    if task.task_type == "summarize":
        payload = {}
        if task.payload:
            try:
                payload = json.loads(task.payload)
            except json.JSONDecodeError:
                payload = {}
        provider = payload.get("provider") or "hailo"
        if provider == "hailo" and (status.status != "available" or status.throttled):
            task.status = "deferred"
            task.error = status.detail or "accelerator unavailable"
            task.completed_at = datetime.utcnow()
            db.commit()
            return
        source_id = payload.get("source_id")
        text_in = payload.get("text")
        model = payload.get("model")
        max_tokens = payload.get("max_input_tokens")
        summary, error = summarize_text(text_in or "", provider, model, max_tokens)
        if error:
            task.status = "failed"
            task.error = error
            task.completed_at = datetime.utcnow()
            db.commit()
            return
        if source_id:
            source = db.query(SourceRecord).filter(SourceRecord.id == source_id).first()
            if source:
                source.summary_text = summary
                source.summary_provider = provider
                source.summary_model = model
                source.summary_created_at = datetime.utcnow()
        task.status = "completed"
        task.completed_at = datetime.utcnow()
        task.error = None
        db.commit()
        return

    if task.task_type == "whisper_transcribe":
        payload = {}
        if task.payload:
            try:
                payload = json.loads(task.payload)
            except json.JSONDecodeError:
                payload = {}
        media_path = payload.get("media_path")
        text_out, error = transcribe_audio(media_path)
        if error and error.startswith("accelerator_"):
            settings = _get_inference_settings(db)
            if settings and settings.inference_enabled and settings.inference_url:
                text_out, error = _delegate_to_server(settings.inference_url, media_path)
        if error:
            task.status = "failed"
            task.error = error
            task.completed_at = datetime.utcnow()
            db.commit()
            return
        meeting_id = payload.get("meeting_id")
        person_id = payload.get("person_id")
        people_ids = payload.get("people_ids")
        job = IngestionJob(
            id="j_" + uuid4().hex,
            meeting_id=meeting_id,
            person_id=person_id,
            payload=text_out,
            capture_type="transcript",
            people_ids=people_ids,
            relevant_at=None,
            commitment_relevant_by=None,
            index_in_memory=False,
            status="queued",
        )
        db.add(job)
        task.status = "completed"
        task.completed_at = datetime.utcnow()
        task.error = None
        db.commit()
        return

    # Placeholder for accelerator execution.
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
