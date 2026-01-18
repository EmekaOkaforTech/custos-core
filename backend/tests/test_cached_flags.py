from datetime import datetime

from fastapi.testclient import TestClient

from app.db import init_db


def test_cached_flags_in_briefings(test_app):
    init_db()
    client = TestClient(test_app)
    cached_at = datetime.utcnow().isoformat()
    response = client.get(f"/api/briefings/today?cached=1&offline=1&cached_at={cached_at}")
    assert response.status_code == 200
    data = response.json()
    assert data["cached"] is True
    assert data["offline"] is True
    assert data["updated_at"].startswith(cached_at[:16])
