def test_people_list_returns_people(test_app):
    from app.db import SessionLocal, init_db
    from app.models.person import Person

    init_db()
    session = SessionLocal()
    try:
        session.add(Person(id="p_1", name="Alex", type="person", last_interaction_at=None))
        session.add(Person(id="p_2", name="Zoe", type="person", last_interaction_at=None))
        session.commit()
    finally:
        session.close()

    from fastapi.testclient import TestClient

    client = TestClient(test_app)
    response = client.get("/api/people")
    assert response.status_code == 200
    data = response.json()
    assert [person["name"] for person in data] == ["Alex", "Zoe"]
