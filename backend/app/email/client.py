from __future__ import annotations

import email
import imaplib
from dataclasses import dataclass
from datetime import datetime
from email.header import decode_header
from email.utils import parsedate_to_datetime
from typing import Iterable, List


@dataclass
class EmailEnvelope:
    uid: int
    message_id: str
    thread_id: str
    subject: str | None
    from_email: str | None
    to_emails: List[str]
    sent_at: datetime | None
    body: str


def _decode_header(value: str | None) -> str | None:
    if not value:
        return None
    try:
        parts = decode_header(value)
    except Exception:
        return value
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            try:
                decoded.append(part.decode(charset or 'utf-8', errors='ignore'))
            except Exception:
                decoded.append(part.decode('utf-8', errors='ignore'))
        else:
            decoded.append(part)
    return ''.join(decoded).strip()


def _extract_body(msg: email.message.Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            disp = part.get('Content-Disposition', '')
            if ctype == 'text/plain' and 'attachment' not in disp:
                payload = part.get_payload(decode=True)
                if payload is None:
                    continue
                try:
                    return payload.decode(part.get_content_charset() or 'utf-8', errors='ignore')
                except Exception:
                    return payload.decode('utf-8', errors='ignore')
        return ''
    payload = msg.get_payload(decode=True)
    if payload is None:
        return ''
    try:
        return payload.decode(msg.get_content_charset() or 'utf-8', errors='ignore')
    except Exception:
        return payload.decode('utf-8', errors='ignore')


def _parse_addresses(value: str | None) -> List[str]:
    if not value:
        return []
    addresses = []
    for part in value.split(','):
        if '<' in part and '>' in part:
            addr = part.split('<', 1)[1].split('>', 1)[0].strip()
        else:
            addr = part.strip()
        if addr:
            addresses.append(addr)
    return addresses


def _thread_id(message_id: str | None, references: str | None, in_reply_to: str | None) -> str:
    if references:
        refs = [ref.strip() for ref in references.split() if ref.strip()]
        if refs:
            return refs[0]
    if in_reply_to:
        return in_reply_to.strip()
    return message_id or ''


def connect_imap(host: str, port: int, username: str, password: str | None, use_tls: bool = True) -> imaplib.IMAP4:
    if use_tls:
        client = imaplib.IMAP4_SSL(host, port)
    else:
        client = imaplib.IMAP4(host, port)
    client.login(username, password or '')
    return client


def fetch_messages(client: imaplib.IMAP4, since_uid: int | None = None, mailbox: str = 'INBOX') -> Iterable[EmailEnvelope]:
    client.select(mailbox)
    criteria = 'ALL'
    if since_uid:
        criteria = f'UID {since_uid + 1}:*'
    result, data = client.uid('search', None, criteria)
    if result != 'OK':
        return []
    uids = data[0].split()
    envelopes: List[EmailEnvelope] = []
    for uid in uids:
        result, msg_data = client.uid('fetch', uid, '(RFC822)')
        if result != 'OK' or not msg_data:
            continue
        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)
        message_id = msg.get('Message-ID') or f'<uid-{uid.decode() if isinstance(uid, bytes) else uid}>'
        subject = _decode_header(msg.get('Subject'))
        from_email = _parse_addresses(msg.get('From'))
        to_emails = _parse_addresses(msg.get('To'))
        sent_at = None
        try:
            sent_at = parsedate_to_datetime(msg.get('Date')) if msg.get('Date') else None
        except Exception:
            sent_at = None
        references = msg.get('References')
        in_reply_to = msg.get('In-Reply-To')
        thread = _thread_id(message_id, references, in_reply_to)
        body = _extract_body(msg)
        envelopes.append(
            EmailEnvelope(
                uid=int(uid),
                message_id=message_id,
                thread_id=thread,
                subject=subject,
                from_email=from_email[0] if from_email else None,
                to_emails=to_emails,
                sent_at=sent_at,
                body=body,
            )
        )
    return envelopes
