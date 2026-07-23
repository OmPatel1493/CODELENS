"""RAG answer-layer tests — service logic and the /ask endpoint.

The LLM and retrieval are mocked, so these are fast and never hit the network.
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.code_chunk import ChunkKind
from app.models.repository import Repository, RepoStatus
from app.schemas.search import SearchHit
from app.services import answer_service, ingestion_service, search_service

CREDS = {"email": "ask@codelens.io", "password": "supersecret1"}


def _auth_headers(client: TestClient) -> dict[str, str]:
    client.post("/api/auth/register", json=CREDS)
    token = client.post("/api/auth/login", json=CREDS).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _hit(**kw) -> SearchHit:
    base = dict(
        chunk_id=1,
        file_path="src/signer.py",
        symbol_name="verify_signature",
        kind=ChunkKind.function,
        start_line=10,
        end_line=20,
        snippet="def verify_signature(...): ...",
        score=0.8,
    )
    base.update(kw)
    return SearchHit(**base)


# ── Service ──────────────────────────────────────────────────────


def test_build_context_numbers_and_labels_chunks():
    ctx = answer_service._build_context([_hit(), _hit(file_path="a.py", symbol_name=None)])
    assert "[1] src/signer.py :: verify_signature (lines 10-20)" in ctx
    assert "[2] a.py (lines 10-20)" in ctx  # no "::" when symbol is None
    assert ctx.count("```") == 4  # each snippet fenced


def test_answer_question_synthesizes_over_retrieved(db_session: Session, monkeypatch):
    repo = Repository(id=1, name="r", owner_id=1, status=RepoStatus.ready)
    captured = {}

    monkeypatch.setattr(search_service, "search_repository", lambda db, r, q, limit: [_hit()])

    class _LLM:
        def complete(self, system, user):
            captured["system"] = system
            captured["user"] = user
            return "It's verified in `signer.py` [1]."

    answer_service.get_llm.cache_clear()
    monkeypatch.setattr(answer_service, "get_llm", lambda: _LLM())

    answer, sources = answer_service.answer_question(db_session, repo, "how is it verified?", 6)
    assert answer == "It's verified in `signer.py` [1]."
    assert len(sources) == 1 and sources[0].symbol_name == "verify_signature"
    assert "how is it verified?" in captured["user"]
    assert "[1] src/signer.py" in captured["user"]  # grounding context passed through


def test_answer_question_no_hits_skips_llm(db_session: Session, monkeypatch):
    repo = Repository(id=1, name="r", owner_id=1, status=RepoStatus.ready)
    monkeypatch.setattr(search_service, "search_repository", lambda db, r, q, limit: [])

    def _boom():
        raise AssertionError("LLM must not be called when there are no hits")

    monkeypatch.setattr(answer_service, "get_llm", _boom)
    answer, sources = answer_service.answer_question(db_session, repo, "anything?", 6)
    assert sources == [] and "couldn't find" in answer.lower()


# ── Endpoint ─────────────────────────────────────────────────────


def test_ask_requires_auth(client: TestClient):
    assert client.post("/api/repositories/1/ask", json={"query": "x"}).status_code == 401


def test_ask_409_when_repo_not_ready(client: TestClient, monkeypatch):
    monkeypatch.setattr(ingestion_service, "run_ingestion", lambda *a, **k: None)
    headers = _auth_headers(client)
    repo = client.post(
        "/api/repositories", json={"url": "https://github.com/pallets/flask"}, headers=headers
    ).json()
    resp = client.post(
        f"/api/repositories/{repo['id']}/ask", json={"query": "how?"}, headers=headers
    )
    assert resp.status_code == 409


def test_ask_503_when_llm_not_configured(client: TestClient, db_session: Session, monkeypatch):
    monkeypatch.setattr(ingestion_service, "run_ingestion", lambda *a, **k: None)
    headers = _auth_headers(client)
    created = client.post(
        "/api/repositories", json={"url": "https://github.com/pallets/flask"}, headers=headers
    ).json()
    repo = db_session.get(Repository, created["id"])
    repo.status = RepoStatus.ready
    db_session.commit()
    monkeypatch.setattr(search_service, "search_repository", lambda db, r, q, limit: [_hit()])

    # Real get_llm with no API key configured → RuntimeError → 503.
    answer_service.get_llm.cache_clear()
    monkeypatch.setattr(answer_service.settings, "LLM_API_KEY", "")
    resp = client.post(
        f"/api/repositories/{created['id']}/ask", json={"query": "how?"}, headers=headers
    )
    assert resp.status_code == 503
    answer_service.get_llm.cache_clear()


def test_ask_returns_answer_and_sources(client: TestClient, db_session: Session, monkeypatch):
    monkeypatch.setattr(ingestion_service, "run_ingestion", lambda *a, **k: None)
    headers = _auth_headers(client)
    created = client.post(
        "/api/repositories", json={"url": "https://github.com/pallets/flask"}, headers=headers
    ).json()
    repo = db_session.get(Repository, created["id"])
    repo.status = RepoStatus.ready
    db_session.commit()

    monkeypatch.setattr(
        answer_service,
        "answer_question",
        lambda db, r, q, limit: ("Routing lives in `app.py` [1].", [_hit(file_path="app.py")]),
    )
    resp = client.post(
        f"/api/repositories/{created['id']}/ask",
        json={"query": "where is routing?"},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["answer"] == "Routing lives in `app.py` [1]."
    assert body["sources"][0]["file_path"] == "app.py"
