"""AI code-review tests — service logic and the /review endpoint (LLM + net mocked)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.code_chunk import ChunkKind
from app.models.repository import Repository, RepoStatus
from app.schemas.search import SearchHit
from app.services import answer_service, ingestion_service, review_service, search_service

CREDS = {"email": "review@codelens.io", "password": "supersecret1"}

_DIFF = """diff --git a/src/auth.py b/src/auth.py
index 1111111..2222222 100644
--- a/src/auth.py
+++ b/src/auth.py
@@ -10,3 +10,4 @@ def login(user):
     token = make_token(user)
+    logging.info(f"issued token {token}")
     return token
"""


def _auth_headers(client: TestClient) -> dict[str, str]:
    client.post("/api/auth/register", json=CREDS)
    token = client.post("/api/auth/login", json=CREDS).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _hit(**kw) -> SearchHit:
    base = dict(
        chunk_id=1,
        file_path="src/auth.py",
        symbol_name="login",
        kind=ChunkKind.function,
        start_line=10,
        end_line=13,
        snippet="def login(user): ...",
        score=0.7,
    )
    base.update(kw)
    return SearchHit(**base)


# ── Service helpers ──────────────────────────────────────────────


def test_parse_pr_url_valid_and_strips_git():
    assert review_service.parse_pr_url("https://github.com/pallets/flask/pull/42") == (
        "pallets",
        "flask",
        42,
    )
    owner, repo, n = review_service.parse_pr_url("github.com/a/b.git/pull/7")
    assert (owner, repo, n) == ("a", "b", 7)


def test_parse_pr_url_invalid():
    with pytest.raises(ValueError, match="valid GitHub pull-request URL"):
        review_service.parse_pr_url("https://github.com/pallets/flask/issues/42")


def test_query_from_diff_pulls_files_and_added_lines():
    q = review_service._query_from_diff(_DIFF)
    assert "src/auth.py" in q
    assert "logging.info" in q  # added line included
    assert "make_token(user)" not in q  # context (unchanged) line excluded


def test_parse_review_valid_json():
    raw = (
        '{"summary": "Logs a secret.", "comments": ['
        '{"severity": "HIGH", "file": "src/auth.py", "line": 11, '
        '"comment": "Do not log the token — leaks credentials."}]}'
    )
    summary, comments = review_service._parse_review(raw)
    assert summary == "Logs a secret."
    assert len(comments) == 1
    assert comments[0].severity == "high"  # lowercased
    assert comments[0].line == 11


def test_parse_review_falls_back_on_bad_json():
    summary, comments = review_service._parse_review("not json at all")
    assert summary == "not json at all" and comments == []


def test_review_runs_over_retrieved_context(db_session: Session, monkeypatch):
    repo = Repository(id=1, name="r", owner_id=1, status=RepoStatus.ready)
    captured = {}
    monkeypatch.setattr(search_service, "search_repository", lambda db, r, q, limit: [_hit()])

    class _LLM:
        def complete(self, system, user, *, json_mode=False, max_tokens=800):
            captured["json_mode"] = json_mode
            captured["user"] = user
            return '{"summary": "ok", "comments": []}'

    monkeypatch.setattr(answer_service, "get_llm", lambda: _LLM())
    summary, comments, sources = review_service.review(db_session, repo, diff=_DIFF, pr_url=None)
    assert summary == "ok" and comments == []
    assert len(sources) == 1
    assert captured["json_mode"] is True  # structured output requested
    assert "src/auth.py" in captured["user"]  # context passed to the model


def test_review_fetches_pr_url(db_session: Session, monkeypatch):
    repo = Repository(id=1, name="r", owner_id=1, status=RepoStatus.ready)
    monkeypatch.setattr(search_service, "search_repository", lambda db, r, q, limit: [])
    monkeypatch.setattr(review_service, "fetch_pr_diff", lambda o, n, num: _DIFF)

    class _LLM:
        def complete(self, system, user, *, json_mode=False, max_tokens=800):
            return '{"summary": "fetched + reviewed", "comments": []}'

    monkeypatch.setattr(answer_service, "get_llm", lambda: _LLM())
    summary, _, _ = review_service.review(
        db_session, repo, diff=None, pr_url="https://github.com/a/b/pull/1"
    )
    assert summary == "fetched + reviewed"


def test_review_rejects_oversized_diff(db_session: Session, monkeypatch):
    repo = Repository(id=1, name="r", owner_id=1, status=RepoStatus.ready)
    monkeypatch.setattr(answer_service.settings, "MAX_DIFF_BYTES", 10)
    with pytest.raises(ValueError, match="too large"):
        review_service.review(db_session, repo, diff=_DIFF, pr_url=None)


# ── Endpoint ─────────────────────────────────────────────────────


def test_review_requires_auth(client: TestClient):
    assert client.post("/api/repositories/1/review", json={"diff": _DIFF}).status_code == 401


def test_review_422_when_no_source(client: TestClient, monkeypatch):
    monkeypatch.setattr(ingestion_service, "run_ingestion", lambda *a, **k: None)
    headers = _auth_headers(client)
    created = client.post(
        "/api/repositories", json={"url": "https://github.com/pallets/flask"}, headers=headers
    ).json()
    # Neither diff nor pr_url → schema validation rejects it.
    resp = client.post(f"/api/repositories/{created['id']}/review", json={}, headers=headers)
    assert resp.status_code == 422


def test_review_returns_findings(client: TestClient, db_session: Session, monkeypatch):
    monkeypatch.setattr(ingestion_service, "run_ingestion", lambda *a, **k: None)
    headers = _auth_headers(client)
    created = client.post(
        "/api/repositories", json={"url": "https://github.com/pallets/flask"}, headers=headers
    ).json()
    repo = db_session.get(Repository, created["id"])
    repo.status = RepoStatus.ready
    db_session.commit()

    from app.schemas.review import ReviewComment

    monkeypatch.setattr(
        review_service,
        "review",
        lambda db, r, *, diff, pr_url: (
            "Logs a secret.",
            [ReviewComment(severity="high", file="src/auth.py", line=11, comment="Leaks token.")],
            [_hit()],
        ),
    )
    resp = client.post(
        f"/api/repositories/{created['id']}/review", json={"diff": _DIFF}, headers=headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["summary"] == "Logs a secret."
    assert body["comments"][0]["severity"] == "high"
    assert body["sources"][0]["file_path"] == "src/auth.py"
