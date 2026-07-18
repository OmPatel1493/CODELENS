"""Auth endpoint tests. The `client` fixture (conftest) uses an in-memory DB."""

from fastapi.testclient import TestClient

REGISTER = "/api/auth/register"
LOGIN = "/api/auth/login"
ME = "/api/auth/me"

CREDS = {"email": "dev@codelens.io", "password": "supersecret1"}


def _register(client: TestClient, **overrides):
    return client.post(REGISTER, json={**CREDS, **overrides})


def test_register_creates_user_without_exposing_password(client: TestClient):
    resp = _register(client)
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == CREDS["email"]
    assert "id" in body and "created_at" in body
    assert "password" not in body and "hashed_password" not in body


def test_register_duplicate_email_conflicts(client: TestClient):
    _register(client)
    resp = _register(client)
    assert resp.status_code == 409


def test_register_rejects_bad_email_and_short_password(client: TestClient):
    assert _register(client, email="not-an-email").status_code == 422
    assert _register(client, password="short").status_code == 422


def test_login_returns_bearer_token(client: TestClient):
    _register(client)
    resp = client.post(LOGIN, json=CREDS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_wrong_password_is_unauthorized(client: TestClient):
    _register(client)
    resp = client.post(LOGIN, json={**CREDS, "password": "wrongpassword"})
    assert resp.status_code == 401


def test_login_unknown_email_is_unauthorized(client: TestClient):
    resp = client.post(LOGIN, json=CREDS)
    assert resp.status_code == 401


def test_me_requires_authentication(client: TestClient):
    assert client.get(ME).status_code == 401
    assert client.get(ME, headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_me_returns_current_user_with_valid_token(client: TestClient):
    _register(client)
    token = client.post(LOGIN, json=CREDS).json()["access_token"]
    resp = client.get(ME, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == CREDS["email"]
