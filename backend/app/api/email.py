from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.email.client import connect_imap
from app.email.runner import poll_email
from app.models.email_connection import EmailConnection

router = APIRouter(prefix="/api/email", tags=["email"])


class EmailConnectionPayload(BaseModel):
    host: str = Field(min_length=1)
    port: int = 993
    username: str = Field(min_length=1)
    password: str | None = None
    use_tls: bool = True
    enabled: bool = False
    poll_interval_minutes: int = 30


@router.get("/connection")
def get_connection(db: Session = Depends(get_db)) -> dict:
    connection = db.query(EmailConnection).first()
    if not connection:
        return {
            "configured": False,
            "enabled": False,
            "host": None,
            "port": 993,
            "username": None,
            "use_tls": True,
            "poll_interval_minutes": 30,
            "last_success": None,
            "last_error": None,
            "last_attempt": None,
        }
    return {
        "configured": True,
        "enabled": connection.enabled,
        "host": connection.host,
        "port": connection.port,
        "username": connection.username,
        "use_tls": connection.use_tls,
        "poll_interval_minutes": connection.poll_interval_minutes,
        "last_success": connection.last_success,
        "last_error": connection.last_error,
        "last_attempt": connection.last_attempt,
    }


@router.post("/connection")
def set_connection(payload: EmailConnectionPayload, db: Session = Depends(get_db)) -> dict:
    connection = db.query(EmailConnection).first()
    if not connection:
        connection = EmailConnection()
        db.add(connection)
    connection.host = payload.host
    connection.port = payload.port
    connection.username = payload.username
    if payload.password is not None:
        connection.password = payload.password
    connection.use_tls = payload.use_tls
    connection.enabled = payload.enabled
    connection.poll_interval_minutes = payload.poll_interval_minutes
    connection.last_attempt = datetime.utcnow()
    db.commit()
    return {"status": "saved"}


@router.post("/connection/test")
def test_connection(payload: EmailConnectionPayload, db: Session = Depends(get_db)) -> dict:
    try:
        client = connect_imap(payload.host, payload.port, payload.username, payload.password, payload.use_tls)
        client.logout()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"IMAP connection failed: {exc}")
    return {"status": "ok"}


@router.post("/poll")
def poll_now() -> dict:
    return poll_email()
