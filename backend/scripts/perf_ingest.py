import sys
import time
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db import SessionLocal, init_db
from app.ingestion.worker import run_once
from app.models.ingestion_job import IngestionJob


def seed_jobs(count: int) -> None:
    init_db()
    session = SessionLocal()
    try:
        for i in range(count):
            job = IngestionJob(
                id=f"j_perf_{uuid4().hex}",
                meeting_id=f"m_perf_{i}",
                payload=f"Blocked by vendor {i}\n- Send update",
                capture_type="notes",
                status="queued",
            )
            session.add(job)
        session.commit()
    finally:
        session.close()


def process_jobs(count: int) -> dict:
    processed = 0
    start = time.perf_counter()
    durations = []
    for _ in range(count):
        job_start = time.perf_counter()
        run_once()
        job_end = time.perf_counter()
        durations.append(job_end - job_start)
        processed += 1
    total = time.perf_counter() - start
    durations.sort()
    p50 = durations[int(0.5 * len(durations)) - 1]
    p95 = durations[int(0.95 * len(durations)) - 1]
    return {
        "processed": processed,
        "jobs_per_min": processed / (total / 60),
        "p50_sec": p50,
        "p95_sec": p95,
    }


if __name__ == "__main__":
    job_count = 100
    seed_jobs(job_count)
    metrics = process_jobs(job_count)
    print(metrics)
