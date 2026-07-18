"""Repository ingestion tests: pure helpers, archive processing, and endpoints.

Endpoint tests stub out `run_ingestion` so no background work (or network) runs —
the background pipeline's logic is covered directly via `process_repository_archive`.
"""

import io
import zipfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.repository import Repository, RepoSource
from app.models.user import User
from app.services import ingestion_service
from app.services.storage import LocalStorageBackend

CREDS = {"email": "dev@codelens.io", "password": "supersecret1"}


def _make_zip(files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buffer.getvalue()


def _auth_headers(client: TestClient) -> dict[str, str]:
    client.post("/api/auth/register", json=CREDS)
    token = client.post("/api/auth/login", json=CREDS).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ── Pure helpers ─────────────────────────────────────────────────


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://github.com/pallets/flask", ("pallets", "flask")),
        ("http://github.com/octocat/Hello-World.git", ("octocat", "Hello-World")),
        ("github.com/a/b/", ("a", "b")),
    ],
)
def test_parse_github_url_valid(url, expected):
    assert ingestion_service.parse_github_url(url) == expected


@pytest.mark.parametrize("url", ["https://gitlab.com/a/b", "not a url", "https://github.com/only"])
def test_parse_github_url_invalid(url):
    with pytest.raises(ValueError):
        ingestion_service.parse_github_url(url)


def test_count_files_in_zip():
    data = _make_zip({"a.py": b"x", "pkg/b.py": b"y"})
    assert ingestion_service.count_files_in_zip(data) == 2


# ── Background processing (direct, no server/network) ────────────


def test_archive_repository(db_session: Session, tmp_path):
    user = User(email="dev@codelens.io", hashed_password="x")
    db_session.add(user)
    db_session.commit()
    repo = Repository(owner_id=user.id, name="demo", source=RepoSource.upload)
    db_session.add(repo)
    db_session.commit()

    storage = LocalStorageBackend(str(tmp_path))
    data = _make_zip({"main.py": b"print(1)", "util/helpers.py": b"pass"})

    ingestion_service.archive_repository(db_session, storage, repo, data, "zip")

    assert repo.file_count == 2
    assert repo.archive_key == f"repositories/{repo.id}/source.zip"
    assert storage.exists(repo.archive_key)


# ── Endpoints ────────────────────────────────────────────────────


def test_list_requires_auth(client: TestClient):
    assert client.get("/api/repositories").status_code == 401


def test_ingest_github_creates_pending_repo(client: TestClient, monkeypatch):
    monkeypatch.setattr(ingestion_service, "run_ingestion", lambda *a, **k: None)
    headers = _auth_headers(client)

    resp = client.post(
        "/api/repositories", json={"url": "https://github.com/pallets/flask"}, headers=headers
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "flask"
    assert body["source"] == "github"
    assert body["status"] == "pending"


def test_ingest_github_rejects_bad_url(client: TestClient, monkeypatch):
    monkeypatch.setattr(ingestion_service, "run_ingestion", lambda *a, **k: None)
    headers = _auth_headers(client)
    resp = client.post("/api/repositories", json={"url": "https://gitlab.com/a/b"}, headers=headers)
    assert resp.status_code == 422


def test_upload_requires_zip(client: TestClient, monkeypatch):
    monkeypatch.setattr(ingestion_service, "run_ingestion", lambda *a, **k: None)
    headers = _auth_headers(client)
    resp = client.post(
        "/api/repositories/upload",
        data={"name": "demo"},
        files={"file": ("repo.txt", b"nope", "text/plain")},
        headers=headers,
    )
    assert resp.status_code == 422


def test_upload_creates_repo(client: TestClient, monkeypatch):
    monkeypatch.setattr(ingestion_service, "run_ingestion", lambda *a, **k: None)
    headers = _auth_headers(client)
    resp = client.post(
        "/api/repositories/upload",
        data={"name": "my-zip"},
        files={"file": ("repo.zip", _make_zip({"a.py": b"x"}), "application/zip")},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["source"] == "upload"


def test_list_get_and_delete(client: TestClient, monkeypatch):
    monkeypatch.setattr(ingestion_service, "run_ingestion", lambda *a, **k: None)
    headers = _auth_headers(client)
    created = client.post(
        "/api/repositories", json={"url": "https://github.com/pallets/flask"}, headers=headers
    ).json()

    listed = client.get("/api/repositories", headers=headers).json()
    assert len(listed) == 1 and listed[0]["id"] == created["id"]

    assert client.get(f"/api/repositories/{created['id']}", headers=headers).status_code == 200
    assert client.get("/api/repositories/9999", headers=headers).status_code == 404

    assert client.delete(f"/api/repositories/{created['id']}", headers=headers).status_code == 204
    assert client.get(f"/api/repositories/{created['id']}", headers=headers).status_code == 404
