"""Health endpoint tests. The `client` fixture (conftest) uses an in-memory DB."""

from fastapi.testclient import TestClient


def test_health_returns_ok(client: TestClient):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["app"] == "CodeLens API"


def test_health_db_reachable(client: TestClient):
    response = client.get("/api/health/db")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "reachable"}
