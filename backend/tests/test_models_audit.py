def test_audit_log_on_create(test_app):
    from datetime import datetime

    from app.db import SessionLocal, init_db
    from app.models.audit_log import AuditLog
    from app.models.person import Person

    init_db()
    session = SessionLocal()
    try:
        person = Person(id="p_1", name="Northwind", type="org", last_interaction_at=datetime.utcnow())
        session.add(person)
        session.commit()
        audit_entries = session.query(AuditLog).all()
        assert audit_entries
        assert audit_entries[0].action == "create"
        assert audit_entries[0].entity_type == "Person"
    finally:
        session.close()
