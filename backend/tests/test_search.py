"""Semantic search tests — service logic and the endpoint (search mocked)."""

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.code_chunk import ChunkKind, CodeChunk
from app.models.repository import Repository, RepoSource, RepoStatus
from app.models.search_log import SearchLog
from app.models.user import User
from app.schemas.search import SearchHit
from app.services import ingestion_service, search_service

CREDS = {"email": "search@codelens.io", "password": "supersecret1"}


def _auth_headers(client: TestClient) -> dict[str, str]:
    client.post("/api/auth/register", json=CREDS)
    token = client.post("/api/auth/login", json=CREDS).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_search_service_ranks_by_score_and_logs(db_session: Session, monkeypatch):
    user = User(email="s@codelens.io", hashed_password="x")
    db_session.add(user)
    db_session.commit()
    repo = Repository(
        owner_id=user.id, name="demo", source=RepoSource.upload, status=RepoStatus.ready
    )
    db_session.add(repo)
    db_session.commit()
    c1 = CodeChunk(
        repository_id=repo.id,
        file_path="auth.py",
        symbol_name="authenticate",
        kind=ChunkKind.function,
        start_line=1,
        end_line=5,
        content="def authenticate(): ...",
    )
    c2 = CodeChunk(
        repository_id=repo.id,
        file_path="utils.py",
        symbol_name="helper",
        kind=ChunkKind.function,
        start_line=1,
        end_line=2,
        content="def helper(): ...",
    )
    db_session.add_all([c1, c2])
    db_session.commit()

    monkeypatch.setattr(search_service.embedder, "embed_query", lambda q: [0.1, 0.2, 0.3])
    monkeypatch.setattr(
        search_service.vector_store,
        "query",
        lambda repo_id, vec, n_results: [
            {"id": str(c1.id), "distance": 0.1, "document": "", "metadata": {}},
            {"id": str(c2.id), "distance": 0.7, "document": "", "metadata": {}},
        ],
    )

    results = search_service.search_repository(db_session, repo, "how does login work", 5)

    assert [r.symbol_name for r in results] == ["authenticate", "helper"]
    assert results[0].score > results[1].score  # closer distance → higher score
    assert db_session.scalar(select(func.count()).select_from(SearchLog)) == 1


def test_search_requires_auth(client: TestClient):
    assert client.post("/api/repositories/1/search", json={"query": "x"}).status_code == 401


def test_search_409_when_repo_not_ready(client: TestClient, monkeypatch):
    monkeypatch.setattr(ingestion_service, "run_ingestion", lambda *a, **k: None)
    headers = _auth_headers(client)
    repo = client.post(
        "/api/repositories", json={"url": "https://github.com/pallets/flask"}, headers=headers
    ).json()
    resp = client.post(
        f"/api/repositories/{repo['id']}/search", json={"query": "routing"}, headers=headers
    )
    assert resp.status_code == 409  # still pending, not indexed


def test_search_returns_results_for_ready_repo(
    client: TestClient, db_session: Session, monkeypatch
):
    monkeypatch.setattr(ingestion_service, "run_ingestion", lambda *a, **k: None)
    headers = _auth_headers(client)
    created = client.post(
        "/api/repositories", json={"url": "https://github.com/pallets/flask"}, headers=headers
    ).json()

    # Flip to ready (same session the app uses) and stub the search itself.
    repo = db_session.get(Repository, created["id"])
    repo.status = RepoStatus.ready
    db_session.commit()
    monkeypatch.setattr(
        search_service,
        "search_repository",
        lambda db, r, q, limit: [
            SearchHit(
                chunk_id=1,
                file_path="app.py",
                symbol_name="route",
                kind=ChunkKind.function,
                start_line=1,
                end_line=3,
                snippet="def route(): ...",
                score=0.92,
            )
        ],
    )

    resp = client.post(
        f"/api/repositories/{created['id']}/search",
        json={"query": "where are routes defined"},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["query"] == "where are routes defined"
    assert body["results"][0]["symbol_name"] == "route"
    assert body["results"][0]["score"] == 0.92
