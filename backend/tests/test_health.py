"""Smoke test for the health endpoint.

Uses FastAPI's TestClient (backed by httpx) which exercises the full app —
routing, middleware, serialization — without running a real server.
"""

from fastapi.testclient import TestClient

from app.main import create_app

client = TestClient(create_app())


def test_health_returns_ok():
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["app"] == "CodeLens API"
