"""Bug-localization tests: log parsing, file ranking + boosting, endpoints, analytics."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.code_chunk import ChunkKind, CodeChunk
from app.models.repository import Repository, RepoSource, RepoStatus
from app.models.search_log import SearchLog
from app.models.user import User
from app.services import bug_localization_service, ingestion_service, log_parser

CREDS = {"email": "bug@codelens.io", "password": "supersecret1"}

PY_TRACE = """Traceback (most recent call last):
  File "app/auth.py", line 42, in authenticate_user
    return create_token(user.id)
AttributeError: 'NoneType' object has no attribute 'id'
"""


def _auth_headers(client: TestClient) -> dict[str, str]:
    client.post("/api/auth/register", json=CREDS)
    token = client.post("/api/auth/login", json=CREDS).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ── Log parser ───────────────────────────────────────────────────


def test_parse_python_traceback():
    parsed = log_parser.parse_log(PY_TRACE)
    assert parsed.error_type == "AttributeError"
    assert any(f.endswith("auth.py") for f in parsed.files)
    assert "authenticate_user" in parsed.symbols
    assert "authenticate_user" in parsed.query_text


def test_parse_js_trace():
    js = (
        "TypeError: Cannot read properties of undefined (reading 'map')\n"
        "    at renderList (src/components/List.tsx:15:20)\n"
    )
    parsed = log_parser.parse_log(js)
    assert parsed.error_type == "TypeError"
    assert any("List.tsx" in f for f in parsed.files)
    assert "renderList" in parsed.symbols


# ── Localization service (mocked embed + vector store) ───────────


def _ready_repo_with_chunks(db: Session):
    user = User(email="loc@codelens.io", hashed_password="x")
    db.add(user)
    db.commit()
    repo = Repository(
        owner_id=user.id, name="demo", source=RepoSource.upload, status=RepoStatus.ready
    )
    db.add(repo)
    db.commit()
    auth = CodeChunk(
        repository_id=repo.id,
        file_path="app/auth.py",
        symbol_name="authenticate_user",
        kind=ChunkKind.function,
        start_line=40,
        end_line=45,
        content="def authenticate_user(): ...",
    )
    util = CodeChunk(
        repository_id=repo.id,
        file_path="app/utils.py",
        symbol_name="helper",
        kind=ChunkKind.function,
        start_line=1,
        end_line=3,
        content="def helper(): ...",
    )
    db.add_all([auth, util])
    db.commit()
    return repo, auth, util


def test_localize_boosts_file_named_in_trace(db_session: Session, monkeypatch):
    repo, auth, util = _ready_repo_with_chunks(db_session)
    monkeypatch.setattr(bug_localization_service.embedder, "embed_query", lambda q: [0.1, 0.2, 0.3])
    # utils is a *closer* semantic match, but auth.py + authenticate_user are named
    # in the trace, so boosting should rank auth first.
    monkeypatch.setattr(
        bug_localization_service.vector_store,
        "query",
        lambda repo_id, vec, n_results: [
            {"id": str(util.id), "distance": 0.2, "document": "", "metadata": {}},
            {"id": str(auth.id), "distance": 0.5, "document": "", "metadata": {}},
        ],
    )

    parsed, results = bug_localization_service.localize(db_session, repo, PY_TRACE, 5)

    assert results[0].file_path == "app/auth.py"
    assert "authenticate_user" in results[0].matched_symbols
    assert "trace" in results[0].reason.lower()


# ── Endpoints ────────────────────────────────────────────────────


def test_localize_requires_auth(client: TestClient):
    assert client.post("/api/repositories/1/localize", json={"log_text": "x"}).status_code == 401


def test_localize_409_when_not_ready(client: TestClient, monkeypatch):
    monkeypatch.setattr(ingestion_service, "run_ingestion", lambda *a, **k: None)
    headers = _auth_headers(client)
    repo = client.post(
        "/api/repositories", json={"url": "https://github.com/pallets/flask"}, headers=headers
    ).json()
    resp = client.post(
        f"/api/repositories/{repo['id']}/localize", json={"log_text": "boom"}, headers=headers
    )
    assert resp.status_code == 409


def test_analytics_breakdown(client: TestClient, db_session: Session, monkeypatch):
    monkeypatch.setattr(ingestion_service, "run_ingestion", lambda *a, **k: None)
    headers = _auth_headers(client)
    created = client.post(
        "/api/repositories", json={"url": "https://github.com/pallets/flask"}, headers=headers
    ).json()
    repo = db_session.get(Repository, created["id"])
    db_session.add_all(
        [
            CodeChunk(
                repository_id=repo.id,
                file_path="a.py",
                symbol_name="f",
                kind=ChunkKind.function,
                start_line=1,
                end_line=2,
                content="x",
            ),
            CodeChunk(
                repository_id=repo.id,
                file_path="b.py",
                symbol_name="C",
                kind=ChunkKind.class_,
                start_line=1,
                end_line=2,
                content="x",
            ),
            CodeChunk(
                repository_id=repo.id,
                file_path="c.js",
                symbol_name=None,
                kind=ChunkKind.file,
                start_line=1,
                end_line=2,
                content="x",
            ),
        ]
    )
    db_session.add(SearchLog(repository_id=repo.id, query="how does auth work", result_count=3))
    db_session.commit()

    body = client.get(f"/api/repositories/{created['id']}/analytics", headers=headers).json()
    assert body["kind_breakdown"]["function"] == 1
    assert body["kind_breakdown"]["class"] == 1
    assert body["language_breakdown"][".py"] == 2
    assert body["recent_searches"][0]["query"] == "how does auth work"
