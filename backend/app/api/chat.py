from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.chat_integration import ChatIntegration
from app.models.chat_message import ChatMessage
from app.models.ingestion_job import IngestionJob
from app.models.meeting import Meeting
from app.models.person import Person

router = APIRouter(prefix="/api/integrations/chat", tags=["chat"])


def _get_integration(db: Session, provider: str) -> ChatIntegration | None:
    return db.query(ChatIntegration).filter(ChatIntegration.provider == provider).first()


def _ensure_meeting(db: Session, provider: str, channel_id: str | None, channel_name: str | None) -> Meeting:
    safe_channel = channel_id or channel_name or "general"
    meeting_id = f"m_chat_{provider}_{safe_channel}"
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if meeting:
        return meeting
    title = channel_name or channel_id or "Chat"
    meeting = Meeting(id=meeting_id, title=f"Chat: {title}")
    db.add(meeting)
    db.flush()
    return meeting


def _ensure_person(db: Session, provider: str, user_id: str | None, user_name: str | None) -> Person | None:
    if not user_id and not user_name:
        return None
    safe_id = user_id or user_name or "unknown"
    person_id = f"p_chat_{provider}_{safe_id}"
    person = db.query(Person).filter(Person.id == person_id).first()
    if person:
        return person
    person = Person(id=person_id, name=user_name or user_id or "Unknown", type="person")
    db.add(person)
    db.flush()
    return person


def _extract_payload(provider: str, payload: dict[str, Any]) -> dict[str, Any]:
    if provider == "slack" and isinstance(payload.get("event"), dict):
        event = payload.get("event")
        return {
            "body": event.get("text"),
            "user_id": event.get("user"),
            "user_name": event.get("user"),
            "channel_id": event.get("channel"),
            "channel_name": payload.get("channel") or payload.get("channel_name"),
            "message_id": event.get("ts"),
            "sent_at": payload.get("event_time"),
        }
    if provider == "discord":
        author = payload.get("author") or {}
        return {
            "body": payload.get("content"),
            "user_id": author.get("id"),
            "user_name": author.get("username"),
            "channel_id": payload.get("channel_id"),
            "channel_name": payload.get("channel_name"),
            "message_id": payload.get("id"),
            "sent_at": payload.get("timestamp"),
        }
    if provider == "teams":
        from_user = payload.get("from") or {}
        conversation = payload.get("conversation") or {}
        return {
            "body": payload.get("text") or payload.get("summary"),
            "user_id": from_user.get("id"),
            "user_name": from_user.get("name"),
            "channel_id": conversation.get("id"),
            "channel_name": conversation.get("name"),
            "message_id": payload.get("id"),
            "sent_at": payload.get("timestamp"),
        }
    return {
        "body": payload.get("text") or payload.get("message") or payload.get("content"),
        "user_id": payload.get("user_id"),
        "user_name": payload.get("user_name"),
        "channel_id": payload.get("channel_id"),
        "channel_name": payload.get("channel_name"),
        "message_id": payload.get("id"),
        "sent_at": payload.get("timestamp"),
    }


def _parse_sent_at(value: Any) -> datetime | None:
    if value is None:
        return None
    try:
        if isinstance(value, (int, float)):
            return datetime.utcfromtimestamp(value)
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


@router.get("/connection/{provider}")
def get_connection(provider: str, db: Session = Depends(get_db)) -> dict:
    integration = _get_integration(db, provider)
    if not integration:
        return {"configured": False, "enabled": False, "provider": provider}
    return {
        "configured": True,
        "enabled": integration.enabled,
        "provider": integration.provider,
    }


@router.post("/connection/{provider}")
def set_connection(provider: str, payload: dict, db: Session = Depends(get_db)) -> dict:
    integration = _get_integration(db, provider)
    if not integration:
        integration = ChatIntegration(id=f"chat_{provider}", provider=provider)
        db.add(integration)
    integration.secret = payload.get("secret")
    integration.enabled = bool(payload.get("enabled"))
    integration.updated_at = datetime.utcnow()
    db.commit()
    return {"status": "saved"}


@router.post("/webhook/{provider}")
async def chat_webhook(provider: str, request: Request, db: Session = Depends(get_db)) -> dict:
    raw_body = await request.body()
    payload = await request.json()

    integration = _get_integration(db, provider)
    if not integration or not integration.enabled:
        raise HTTPException(status_code=400, detail="Chat integration not enabled")

    if integration.secret:
        signature = request.headers.get("X-Custos-Signature")
        expected = hmac.new(integration.secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
        if not signature or not hmac.compare_digest(signature, expected):
            raise HTTPException(status_code=401, detail="Invalid signature")

    extracted = _extract_payload(provider, payload)
    body = extracted.get("body") or ""
    if not body:
        return {"status": "ignored"}

    channel_id = extracted.get("channel_id")
    channel_name = extracted.get("channel_name")
    meeting = _ensure_meeting(db, provider, channel_id, channel_name)
    person = _ensure_person(db, provider, extracted.get("user_id"), extracted.get("user_name"))

    message_id = extracted.get("message_id") or hashlib.sha256(raw_body).hexdigest()
    chat_id = f"chat_{provider}_{message_id}"
    if db.query(ChatMessage).filter(ChatMessage.id == chat_id).first():
        return {"status": "duplicate"}

    sent_at = _parse_sent_at(extracted.get("sent_at"))

    db.add(
        ChatMessage(
            id=chat_id,
            provider=provider,
            channel_id=channel_id,
            channel_name=channel_name,
            user_id=extracted.get("user_id"),
            user_name=extracted.get("user_name"),
            body=body,
            sent_at=sent_at,
            meeting_id=meeting.id,
            person_id=person.id if person else None,
            payload_json=json.dumps(payload),
        )
    )

    job = IngestionJob(
        id=f"j_chat_{hashlib.sha256(raw_body).hexdigest()}",
        meeting_id=meeting.id,
        payload=body,
        capture_type="chat",
        people_ids=json.dumps([person.id] if person else []),
        relevant_at=None,
        commitment_relevant_by=None,
        index_in_memory=False,
        status="queued",
    )
    db.add(job)
    db.commit()
    return {"status": "ok"}
