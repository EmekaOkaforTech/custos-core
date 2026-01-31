"""
Tests for Epic 32: Person Profile Enrichment

Tests for:
- Person role update
- Person tags CRUD
- Person direct notes
- Person profile endpoint with enriched data
"""


def test_person_profile_returns_enriched_data(test_app):
    """Test that GET /api/people/{id} returns profile with role, tags, and timeline summary."""
    from app.db import SessionLocal, init_db
    from app.models.person import Person
    from app.models.person_tag import PersonTag

    init_db()
    session = SessionLocal()
    try:
        person = Person(id="p_profile_1", name="Profile Test", type="person", role="client")
        session.add(person)
        session.add(PersonTag(id="pt_1", person_id="p_profile_1", tag="vip"))
        session.add(PersonTag(id="pt_2", person_id="p_profile_1", tag="priority"))
        session.commit()
    finally:
        session.close()

    from fastapi.testclient import TestClient

    client = TestClient(test_app)
    response = client.get("/api/people/p_profile_1")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Profile Test"
    assert data["role"] == "client"
    assert "vip" in data["tags"]
    assert "priority" in data["tags"]
    assert "timeline_summary" in data


def test_person_role_update(test_app):
    """Test that PATCH /api/people/{id} can update the role."""
    from app.db import SessionLocal, init_db
    from app.models.person import Person

    init_db()
    session = SessionLocal()
    try:
        session.add(Person(id="p_role_1", name="Role Test", type="person", role=None))
        session.commit()
    finally:
        session.close()

    from fastapi.testclient import TestClient

    client = TestClient(test_app)
    response = client.patch("/api/people/p_role_1", json={"role": "colleague"})
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "colleague"

    # Verify the update persisted
    response = client.get("/api/people/p_role_1")
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "colleague"


def test_person_tag_add(test_app):
    """Test that POST /api/people/{id}/tags adds a tag."""
    from app.db import SessionLocal, init_db
    from app.models.person import Person

    init_db()
    session = SessionLocal()
    try:
        session.add(Person(id="p_tag_1", name="Tag Test", type="person"))
        session.commit()
    finally:
        session.close()

    from fastapi.testclient import TestClient

    client = TestClient(test_app)
    response = client.post("/api/people/p_tag_1/tags", json={"tag": "important"})
    assert response.status_code == 201  # Created
    data = response.json()
    assert data["tag"] == "important"
    assert data["person_id"] == "p_tag_1"


def test_person_tag_remove(test_app):
    """Test that DELETE /api/people/{id}/tags/{tag} removes a tag."""
    from app.db import SessionLocal, init_db
    from app.models.person import Person
    from app.models.person_tag import PersonTag

    init_db()
    session = SessionLocal()
    try:
        session.add(Person(id="p_tag_2", name="Tag Remove Test", type="person"))
        session.add(PersonTag(id="pt_remove_1", person_id="p_tag_2", tag="removeme"))
        session.commit()
    finally:
        session.close()

    from fastapi.testclient import TestClient

    client = TestClient(test_app)

    # Verify tag exists
    response = client.get("/api/people/p_tag_2")
    assert response.status_code == 200
    assert "removeme" in response.json()["tags"]

    # Remove the tag
    response = client.delete("/api/people/p_tag_2/tags/removeme")
    assert response.status_code == 204  # No Content

    # Verify tag removed
    response = client.get("/api/people/p_tag_2")
    assert response.status_code == 200
    assert "removeme" not in response.json()["tags"]


def test_person_tag_duplicate_returns_409(test_app):
    """Test that adding a duplicate tag returns 409 Conflict."""
    from app.db import SessionLocal, init_db
    from app.models.person import Person
    from app.models.person_tag import PersonTag

    init_db()
    session = SessionLocal()
    try:
        session.add(Person(id="p_tag_3", name="Tag Dup Test", type="person"))
        session.add(PersonTag(id="pt_dup_1", person_id="p_tag_3", tag="existing"))
        session.commit()
    finally:
        session.close()

    from fastapi.testclient import TestClient

    client = TestClient(test_app)
    response = client.post("/api/people/p_tag_3/tags", json={"tag": "existing"})
    assert response.status_code == 409


def test_people_list_with_filters(test_app):
    """Test that GET /api/people supports role and tag filters."""
    from app.db import SessionLocal, init_db
    from app.models.person import Person
    from app.models.person_tag import PersonTag

    init_db()
    session = SessionLocal()
    try:
        session.add(Person(id="p_filter_1", name="Filter A", type="person", role="client"))
        session.add(Person(id="p_filter_2", name="Filter B", type="person", role="family"))
        session.add(Person(id="p_filter_3", name="Filter C", type="org", role=None))
        session.add(PersonTag(id="pt_f_1", person_id="p_filter_1", tag="vip"))
        session.commit()
    finally:
        session.close()

    from fastapi.testclient import TestClient

    client = TestClient(test_app)

    # Filter by role
    response = client.get("/api/people?role=client")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Filter A"

    # Filter by type
    response = client.get("/api/people?type=org")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Filter C"

    # Filter by tag
    response = client.get("/api/people?tag=vip")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Filter A"


def test_person_not_found(test_app):
    """Test that GET /api/people/{id} returns 404 for non-existent person."""
    from app.db import init_db

    init_db()

    from fastapi.testclient import TestClient

    client = TestClient(test_app)
    response = client.get("/api/people/nonexistent")
    assert response.status_code == 404
