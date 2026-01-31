from fastapi.testclient import TestClient


def test_people_create_and_dedupe(test_app):
    from app.db import init_db

    init_db()
    client = TestClient(test_app)
    create = client.post("/api/people", json={"name": "Jordan Lee", "type": "person"})
    assert create.status_code == 200
    data = create.json()
    assert data["created"] is True
    assert data["name"] == "Jordan Lee"

    dup = client.post("/api/people", json={"name": "jordan lee", "type": "person"})
    assert dup.status_code == 200
    dup_data = dup.json()
    assert dup_data["created"] is False
    assert dup_data["id"] == data["id"]


def test_people_create_invalid_type(test_app):
    from app.db import init_db

    init_db()
    client = TestClient(test_app)
    response = client.post("/api/people", json={"name": "Acme", "type": "invalid"})
    assert response.status_code == 422
