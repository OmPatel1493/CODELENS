"""Explain-feature tests — context building, JSON parsing, and the endpoint."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.code_chunk import ChunkKind, CodeChunk
from app.models.repository import Repository, RepoSource, RepoStatus
from app.models.user import User
from app.services import answer_service, explain_service, ingestion_service

CREDS = {"email": "explain@codelens.io", "password": "supersecret1"}


def _auth_headers(client: TestClient) -> dict[str, str]:
    client.post("/api/auth/register", json=CREDS)
    token = client.post("/api/auth/login", json=CREDS).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _seed_repo(db: Session) -> Repository:
    user = User(email="e@codelens.io", hashed_password="x")
    db.add(user)
    db.commit()
    repo = Repository(
        owner_id=user.id, name="demo", source=RepoSource.github, status=RepoStatus.ready
    )
    db.add(repo)
    db.commit()
    for path, content in [
        ("src/app.py", "def main(): start_server()"),  # entry-point name
        ("src/util/helpers.py", "def slugify(s): return s"),
        ("README.md", "ignored (not indexed as code)"),
    ]:
        db.add(
            CodeChunk(
                repository_id=repo.id,
                file_path=path,
                symbol_name=None,
                kind=ChunkKind.file,
                start_line=1,
                end_line=1,
                content=content,
            )
        )
    db.commit()
    return repo


# ── Service ──────────────────────────────────────────────────────


def test_priority_ranks_entry_points_first():
    assert explain_service._priority("src/app.py") == 0
    assert explain_service._priority("src/main.py") == 0
    assert explain_service._priority("src/util/helpers.py") == 1


def test_repo_context_puts_entry_point_first(db_session: Session):
    repo = _seed_repo(db_session)
    ctx = explain_service._repo_context(db_session, repo)
    assert ctx.index("src/app.py") < ctx.index("src/util/helpers.py")  # entry-point first


def test_file_context_unknown_file_raises(db_session: Session):
    repo = _seed_repo(db_session)
    try:
        explain_service._file_context(db_session, repo, "nope.py")
        raise AssertionError("expected ValueError")
    except ValueError as e:
        assert "No indexed code" in str(e)


def test_parse_valid_json():
    raw = (
        '{"title": "What it does", "summary": "It signs things.", '
        '"sections": [{"heading": "In a nutshell", "body": "It protects data."}], '
        '"glossary": [{"term": "token", "definition": "a secure pass"}]}'
    )
    out = explain_service._parse(raw)
    assert out["title"] == "What it does"
    assert out["sections"][0].heading == "In a nutshell"
    assert out["glossary"][0].term == "token"


def test_parse_falls_back_on_bad_json():
    out = explain_service._parse("not json")
    assert out["summary"] == "not json" and out["sections"] == []


def test_explain_uses_llm_over_repo_context(db_session: Session, monkeypatch):
    repo = _seed_repo(db_session)
    captured = {}

    class _LLM:
        def complete(self, system, user, *, json_mode=False, max_tokens=800):
            captured["json_mode"] = json_mode
            captured["user"] = user
            return '{"title": "T", "summary": "S", "sections": [], "glossary": []}'

    monkeypatch.setattr(answer_service, "get_llm", lambda: _LLM())
    out = explain_service.explain(db_session, repo, "repo", None)
    assert out["scope"] == "repo" and out["title"] == "T"
    assert captured["json_mode"] is True
    assert "src/app.py" in captured["user"]  # real code passed as context


# ── Endpoint ─────────────────────────────────────────────────────


def test_explain_requires_auth(client: TestClient):
    assert client.post("/api/repositories/1/explain", json={"scope": "repo"}).status_code == 401


def test_explain_422_when_file_scope_missing_file(
    client: TestClient, db_session: Session, monkeypatch
):
    monkeypatch.setattr(ingestion_service, "run_ingestion", lambda *a, **k: None)
    headers = _auth_headers(client)
    created = client.post(
        "/api/repositories", json={"url": "https://github.com/pallets/flask"}, headers=headers
    ).json()
    repo = db_session.get(Repository, created["id"])
    repo.status = RepoStatus.ready
    db_session.commit()
    resp = client.post(
        f"/api/repositories/{created['id']}/explain", json={"scope": "file"}, headers=headers
    )
    assert resp.status_code == 422  # schema validator: file scope needs a file


def test_explain_returns_structure(client: TestClient, db_session: Session, monkeypatch):
    monkeypatch.setattr(ingestion_service, "run_ingestion", lambda *a, **k: None)
    headers = _auth_headers(client)
    created = client.post(
        "/api/repositories", json={"url": "https://github.com/pallets/flask"}, headers=headers
    ).json()
    repo = db_session.get(Repository, created["id"])
    repo.status = RepoStatus.ready
    db_session.commit()
    monkeypatch.setattr(
        explain_service,
        "explain",
        lambda db, r, scope, file: {
            "scope": scope,
            "title": "What flask does",
            "summary": "A friendly web toolkit.",
            "sections": [{"heading": "In a nutshell", "body": "It builds websites."}],
            "glossary": [{"term": "web app", "definition": "a program you use in a browser"}],
        },
    )
    resp = client.post(
        f"/api/repositories/{created['id']}/explain", json={"scope": "repo"}, headers=headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "What flask does"
    assert body["sections"][0]["heading"] == "In a nutshell"
    assert body["glossary"][0]["term"] == "web app"
