from uuid import uuid4

from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from . import models
from .models import Base
from .models.audit_log import AuditLog
from .settings import allow_plaintext_db, get_database_key, get_database_url


def create_db_engine():
    database_url = get_database_url()
    connect_args = {"check_same_thread": False}
    engine_kwargs = {"connect_args": connect_args}
    if database_url.startswith("sqlite+pysqlcipher:///") and not allow_plaintext_db():
        key = get_database_key()
        if not key:
            raise RuntimeError("CUSTOS_DATABASE_KEY is required for SQLCipher encryption.")
        url = make_url(database_url)
        if not url.query.get("password"):
            url = url.update_query_dict({"password": key})
            database_url = str(url)
        try:
            import sqlcipher3
        except ImportError as exc:
            raise RuntimeError(
                "SQLCipher driver missing. Install sqlcipher3-binary and avoid conda base."
            ) from exc
        engine_kwargs["module"] = sqlcipher3.dbapi2
    engine = create_engine(database_url, **engine_kwargs)
    if not allow_plaintext_db():
        _attach_sqlcipher_key(engine)
    return engine


def _attach_sqlcipher_key(engine):
    key = get_database_key()
    if not key:
        raise RuntimeError("CUSTOS_DATABASE_KEY is required for SQLCipher encryption.")

    @event.listens_for(engine, "connect")
    def _set_sqlcipher_key(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute(f"PRAGMA key = '{key}';")
        cursor.execute("PRAGMA cipher_version;")
        cipher_version = cursor.fetchone()
        if not cipher_version or not cipher_version[0]:
            raise RuntimeError("SQLCipher is not active. Encryption check failed.")
        cursor.close()


engine = create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    _ = models
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@event.listens_for(SessionLocal, "after_flush")
def write_audit_log(session, _flush_context):
    if session.info.get("audit_skip"):
        return
    entries = []
    for obj in session.new:
        if isinstance(obj, AuditLog):
            continue
        entries.append(_audit_entry("create", obj))
    for obj in session.dirty:
        if isinstance(obj, AuditLog):
            continue
        if session.is_modified(obj, include_collections=False):
            entries.append(_audit_entry("update", obj))
    for obj in session.deleted:
        if isinstance(obj, AuditLog):
            continue
        entries.append(_audit_entry("delete", obj))
    if entries:
        session.info["audit_skip"] = True
        for entry in entries:
            session.add(entry)
        session.info["audit_skip"] = False


def _audit_entry(action, obj):
    entity_type = obj.__class__.__name__
    entity_id = getattr(obj, "id", "unknown")
    return AuditLog(
        id=f"al_{uuid4().hex}",
        actor="system",
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
    )
