from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.ingestion_job import IngestionJob
from app.ops.qdrant_store import query_documents

router = APIRouter(prefix="/api/memory", tags=["memory"])


@router.get("/surface")
def surface_memory(db: Session = Depends(get_db), limit: int = 5) -> dict:
    reflection = (
        db.query(IngestionJob)
        .filter(IngestionJob.capture_type == "reflection")
        .filter(IngestionJob.status == "succeeded")
        .order_by(IngestionJob.completed_at.desc().nulls_last(), IngestionJob.created_at.desc())
        .first()
    )
    if not reflection or not reflection.payload:
        return {"query": None, "items": [], "why": "No reflections captured yet."}

    try:
        results = query_documents(reflection.payload, limit=limit)
    except RuntimeError as exc:
        return {
            "query": None,
            "items": [],
            "why": "Memory store unavailable. Ensure Qdrant is running locally or configured.",
            "error": str(exc),
        }
    allowed_types = {"reflection", "notes"}
    items = []
    for payload in results:
        capture_type = payload.get("capture_type")
        if capture_type and capture_type not in allowed_types:
            continue
        items.append(
            {
                "source_id": payload.get("source_id"),
                "meeting_title": payload.get("meeting_title"),
                "captured_at": payload.get("captured_at"),
                "capture_type": capture_type,
                "excerpt": payload.get("excerpt"),
            }
        )

    items.sort(key=lambda item: item.get("captured_at") or "", reverse=True)
    return {
        "query": {
            "source_id": reflection.source_id,
            "captured_at": reflection.completed_at or reflection.created_at or datetime.utcnow(),
        },
        "items": items,
        "why": "Surfaced because it is semantically related to your most recent reflection.",
        "filters": {"capture_types": sorted(allowed_types)},
    }
