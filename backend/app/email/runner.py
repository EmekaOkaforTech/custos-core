from __future__ import annotations

import json
import time
from datetime import datetime

from app.db import SessionLocal, init_db
from app.email.client import connect_imap, fetch_messages
from app.models.email_connection import EmailConnection
from app.models.email_message import EmailMessage
from app.models.ingestion_job import IngestionJob
from app.models.meeting import Meeting
from app.models.person import Person

DEFAULT_POLL_SECONDS = 1800


def _find_or_create_person(db, email_addr: str | None) -> Person | None:
    if not email_addr:
        return None
    person = db.query(Person).filter(Person.email == email_addr).first()
    if person:
        return person
    safe_id = email_addr.replace("@", "_").replace(".", "_")
    person = Person(id=f"p_{safe_id}", name=email_addr, type="person")
    person.email = email_addr
    db.add(person)
    db.flush()
    return person


def _get_or_create_meeting(db, thread_id: str, subject: str | None, from_email: str | None) -> Meeting:
    existing = db.query(EmailMessage).filter(EmailMessage.thread_id == thread_id).first()
    if existing and existing.meeting_id:
        meeting = db.query(Meeting).filter(Meeting.id == existing.meeting_id).first()
        if meeting:
            return meeting
    title = subject or f"Email from {from_email or unknown}"
    meeting = Meeting(id=f"m_{abs(hash(thread_id))}", title=f"Email: {title}")
    db.add(meeting)
    db.flush()
    return meeting


def poll_email() -> dict:
    init_db()
    db = SessionLocal()
    created = 0
    errors: list[str] = []
    try:
        connection = db.query(EmailConnection).first()
        if not connection or not connection.enabled:
            return {"status": "disabled", "created": 0}
        connection.last_attempt = datetime.utcnow()
        db.commit()
        try:
            client = connect_imap(
                connection.host,
                connection.port,
                connection.username,
                connection.password,
                connection.use_tls,
            )
        except Exception as exc:
            connection.last_error = f"connect_failed:{exc}"
            db.commit()
            return {"status": "error", "created": 0, "error": connection.last_error}
        try:
            envelopes = list(fetch_messages(client, connection.last_uid))
            max_uid = connection.last_uid or 0
            for env in envelopes:
                if env.uid > max_uid:
                    max_uid = env.uid
                if db.query(EmailMessage).filter(EmailMessage.message_id == env.message_id).first():
                    continue
                meeting = _get_or_create_meeting(db, env.thread_id, env.subject, env.from_email)
                people_ids: list[str] = []
                sender = _find_or_create_person(db, env.from_email)
                if sender:
                    people_ids.append(sender.id)
                for addr in env.to_emails:
                    person = _find_or_create_person(db, addr)
                    if person and person.id not in people_ids:
                        people_ids.append(person.id)
                subject = env.subject or "(no subject)"
                body = env.body or ""
                payload = f"Subject: {subject}\n\n{body}".strip()
                job = IngestionJob(
                    id=f"j_email_{env.uid}_{abs(hash(env.message_id))}",
                    meeting_id=meeting.id,
                    payload=payload,
                    capture_type="email",
                    people_ids=json.dumps(people_ids),
                    relevant_at=None,
                    commitment_relevant_by=None,
                    index_in_memory=False,
                    status="queued",
                )
                db.add(job)
                db.add(
                    EmailMessage(
                        message_id=env.message_id,
                        thread_id=env.thread_id,
                        subject=env.subject,
                        from_email=env.from_email,
                        to_emails=json.dumps(env.to_emails),
                        sent_at=env.sent_at,
                        meeting_id=meeting.id,
                        source_id=None,
                    )
                )
                created += 1
            connection.last_uid = max_uid
            connection.last_success = datetime.utcnow()
            connection.last_error = None
            db.commit()
        except Exception as exc:
            db.rollback()
            connection.last_error = f"poll_failed:{exc}"
            db.commit()
            errors.append(connection.last_error)
        finally:
            try:
                client.logout()
            except Exception:
                pass
    finally:
        db.close()
    return {"status": "ok", "created": created, "errors": errors}


def run_forever():
    while True:
        try:
            poll_email()
            interval = DEFAULT_POLL_SECONDS
            db = SessionLocal()
            try:
                connection = db.query(EmailConnection).first()
                if connection and connection.poll_interval_minutes:
                    interval = max(connection.poll_interval_minutes * 60, 60)
            finally:
                db.close()
        except Exception:
            interval = DEFAULT_POLL_SECONDS
        time.sleep(interval)


if __name__ == "__main__":
    run_forever()
