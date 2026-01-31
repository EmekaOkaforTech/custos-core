import json
from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session
from uuid import uuid4

from app.db import get_db
from app.models import IngestionJob, Meeting, QueryHistory, SourceRecord
from app.ops.query_parser import parse_query
from app.ops.qdrant_store import query_documents
from app.ops.summarization import summarize_text
from app.ops.accelerator import get_accelerator_status


router = APIRouter(prefix="/query", tags=["query"])


class QueryParseIn(BaseModel):
    query: str


class QueryParseOut(BaseModel):
    intent: str
    filters: Dict[str, Any]
    tokens: List[str]
    used_llm: bool = False
    note: str | None = None


class QuerySearchIn(BaseModel):
    query: str
    filters: Dict[str, Any] | None = None
    limit: int = 5


class QuerySearchItem(BaseModel):
    source_id: str | None
    meeting_title: str | None
    captured_at: datetime | None
    capture_type: str | None
    excerpt: str | None


class QuerySearchOut(BaseModel):
    items: List[QuerySearchItem]
    vector_count: int
    keyword_count: int


class QueryAnswerOut(BaseModel):
    answer: str
    sources: List[QuerySearchItem]
    note: str | None = None


class QueryHistoryOut(BaseModel):
    id: str
    query_text: str
    intent: str | None
    filters: Dict[str, Any] | None
    created_at: datetime


@router.post("/parse", response_model=QueryParseOut)
def parse_query_endpoint(payload: QueryParseIn):
    parsed, used_llm = parse_query(payload.query)
    return QueryParseOut(
        intent=parsed.get("intent", "search"),
        filters=parsed.get("filters", {}),
        tokens=parsed.get("tokens", []),
        used_llm=used_llm,
        note=parsed.get("note"),
    )


@router.post("/search", response_model=QuerySearchOut)
def search_query(payload: QuerySearchIn, db: Session = Depends(get_db)):
    query_text = (payload.query or "").strip()
    if not query_text:
        raise HTTPException(status_code=400, detail="query required")
    limit = max(1, min(payload.limit, 20))
    filters = payload.filters or {}

    items: List[QuerySearchItem] = []
    seen: set[str] = set()

    # Vector search
    vector_results: List[dict[str, Any]] = []
    try:
        vector_results = query_documents(query_text, limit=limit)
    except Exception:
        vector_results = []

    for result in vector_results:
        source_id = result.get("source_id")
        if source_id and source_id in seen:
            continue
        seen.add(source_id or f"vector:{len(seen)}")
        items.append(
            QuerySearchItem(
                source_id=source_id,
                meeting_title=result.get("meeting_title"),
                captured_at=_parse_dt(result.get("captured_at")),
                capture_type=result.get("capture_type"),
                excerpt=result.get("excerpt"),
            )
        )

    # Keyword search
    keyword_query = (
        db.query(SourceRecord, IngestionJob, Meeting)
        .join(IngestionJob, IngestionJob.source_id == SourceRecord.id)
        .outerjoin(Meeting, Meeting.id == SourceRecord.meeting_id)
        .filter(
            or_(
                IngestionJob.payload.ilike(f"%{query_text}%"),
                SourceRecord.summary_text.ilike(f"%{query_text}%"),
            )
        )
    )

    capture_types = filters.get("capture_types")
    if capture_types:
        keyword_query = keyword_query.filter(SourceRecord.capture_type.in_(capture_types))

    start = filters.get("start")
    end = filters.get("end")
    if start:
        keyword_query = keyword_query.filter(SourceRecord.captured_at >= _safe_dt(start))
    if end:
        keyword_query = keyword_query.filter(SourceRecord.captured_at <= _safe_dt(end))

    keyword_rows = keyword_query.order_by(SourceRecord.captured_at.desc()).limit(limit).all()
    keyword_count = 0
    for source, job, meeting in keyword_rows:
        keyword_count += 1
        source_id = source.id
        if source_id in seen:
            continue
        seen.add(source_id)
        excerpt = _excerpt(job.payload or source.summary_text or "")
        items.append(
            QuerySearchItem(
                source_id=source_id,
                meeting_title=meeting.title if meeting else None,
                captured_at=source.captured_at,
                capture_type=source.capture_type,
                excerpt=excerpt,
            )
        )

    return QuerySearchOut(items=items[:limit], vector_count=len(vector_results), keyword_count=keyword_count)


@router.post("/answer", response_model=QueryAnswerOut)
def answer_query(payload: QuerySearchIn, db: Session = Depends(get_db)):
    search = search_query(payload, db)
    if not search.items:
        return QueryAnswerOut(answer="I don't know yet.", sources=[], note="no_sources")

    text_blob = "\n\n".join([item.excerpt or "" for item in search.items if item.excerpt])
    if not text_blob:
        return QueryAnswerOut(answer="I don't know yet.", sources=search.items, note="no_text")

    # Use accelerator summarization if available; otherwise return a concise excerpt list.
    status = get_accelerator_status()
    if status.status != "available":
        return QueryAnswerOut(
            answer="\n".join([item.excerpt for item in search.items if item.excerpt][:3]),
            sources=search.items,
            note="accelerator_unavailable",
        )

    summary, error, _model = summarize_text(text_blob, "hailo", None, 2000)
    if error or not summary:
        return QueryAnswerOut(answer="I don't know yet.", sources=search.items, note=error or "summary_error")

    return QueryAnswerOut(answer=summary, sources=search.items)


@router.get("/history", response_model=List[QueryHistoryOut])
def query_history(db: Session = Depends(get_db)):
    rows = db.query(QueryHistory).order_by(QueryHistory.created_at.desc()).limit(20).all()
    output = []
    for row in rows:
        output.append(
            QueryHistoryOut(
                id=row.id,
                query_text=row.query_text,
                intent=row.intent,
                filters=json.loads(row.filters) if row.filters else None,
                created_at=row.created_at,
            )
        )
    return output


@router.post("/history")
def save_query_history(payload: QueryParseOut, db: Session = Depends(get_db)):
    entry = QueryHistory(
        id=f"qh_{uuid4().hex}",
        query_text=" ".join(payload.tokens) if payload.tokens else "",
        intent=payload.intent,
        filters=json.dumps(payload.filters or {}),
        created_at=datetime.utcnow(),
    )
    db.add(entry)
    db.commit()
    return {"id": entry.id}


def _excerpt(text: str, limit: int = 220) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "…"


def _safe_dt(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return datetime.utcnow()


def _parse_dt(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None
