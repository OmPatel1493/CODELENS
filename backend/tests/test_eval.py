"""Retrieval-eval tests — pure metrics, the benchmark runner, and the endpoint."""

import math

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.eval import benchmark
from app.models.code_chunk import ChunkKind
from app.models.repository import Repository, RepoStatus
from app.schemas.search import SearchHit
from app.services import ingestion_service, metrics, search_service

CREDS = {"email": "eval@codelens.io", "password": "supersecret1"}


def _auth_headers(client: TestClient) -> dict[str, str]:
    client.post("/api/auth/register", json=CREDS)
    token = client.post("/api/auth/login", json=CREDS).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _hit(path: str) -> SearchHit:
    return SearchHit(
        chunk_id=1,
        file_path=path,
        symbol_name=None,
        kind=ChunkKind.file,
        start_line=1,
        end_line=1,
        snippet="…",
        score=0.5,
    )


# ── Pure metrics ─────────────────────────────────────────────────


def test_recall_at_k():
    assert metrics.recall_at_k([True, False, False], 1, 1) == 1.0
    assert metrics.recall_at_k([False, True, False], 1, 1) == 0.0
    assert metrics.recall_at_k([False, True, False], 5, 1) == 1.0
    assert metrics.recall_at_k([True, False, True], 5, 2) == 1.0  # both relevant found


def test_reciprocal_rank():
    assert metrics.reciprocal_rank([False, False, True]) == 1 / 3
    assert metrics.reciprocal_rank([True]) == 1.0
    assert metrics.reciprocal_rank([False, False]) == 0.0


def test_average_precision():
    # hits at ranks 1 and 3 → (1/1 + 2/3) / 2
    ap = metrics.average_precision([True, False, True], 2)
    assert math.isclose(ap, (1.0 + 2 / 3) / 2)
    assert metrics.average_precision([False, False], 1) == 0.0


def test_aggregate_means_across_queries():
    per_q = [
        {"recall_at_1": 1.0, "recall_at_5": 1.0, "reciprocal_rank": 1.0, "average_precision": 1.0},
        {"recall_at_1": 0.0, "recall_at_5": 1.0, "reciprocal_rank": 0.5, "average_precision": 0.5},
    ]
    agg = metrics.aggregate(per_q, ks=(1, 5))
    assert agg["queries"] == 2
    assert agg["recall_at_1"] == 0.5
    assert agg["recall_at_5"] == 1.0
    assert agg["mrr"] == 0.75


# ── Benchmark runner ─────────────────────────────────────────────


def test_run_benchmark_scores_against_search(db_session: Session, monkeypatch):
    repo = Repository(id=1, name="itsdangerous", owner_id=1, status=RepoStatus.ready)
    # Every query retrieves signer.py at rank 1; only the 2 signer.py queries are hits.
    monkeypatch.setattr(
        search_service,
        "search_repository",
        lambda db, r, q, limit: [_hit("src/itsdangerous/signer.py")],
    )
    result = benchmark.run_benchmark(db_session, repo)
    assert result["repo"] == "itsdangerous"
    assert result["summary"]["queries"] == 8
    assert result["summary"]["recall_at_1"] == 0.25  # 2 of 8 queries expect signer.py
    assert result["summary"]["mrr"] == 0.25


def test_run_benchmark_unknown_repo_raises(db_session: Session):
    repo = Repository(id=1, name="some-random-repo", owner_id=1, status=RepoStatus.ready)
    try:
        benchmark.run_benchmark(db_session, repo)
        raise AssertionError("expected ValueError")
    except ValueError as e:
        assert "No benchmark" in str(e)


def test_is_relevant_uses_strict_suffix_not_substring():
    assert benchmark._is_relevant("src/pkg/signer.py", ["signer.py"])
    assert benchmark._is_relevant("signer.py", ["signer.py"])
    # a test file must NOT count as the source file
    assert not benchmark._is_relevant("tests/test_signer.py", ["signer.py"])


def test_run_benchmark_dedupes_files_and_bounds_metrics(db_session: Session, monkeypatch):
    repo = Repository(id=1, name="itsdangerous", owner_id=1, status=RepoStatus.ready)
    # A test file (not relevant) then two chunks of the source file (one distinct file).
    monkeypatch.setattr(
        search_service,
        "search_repository",
        lambda db, r, q, limit: [
            _hit("tests/test_signer.py"),
            _hit("src/itsdangerous/signer.py"),
            _hit("src/itsdangerous/signer.py"),
        ],
    )
    result = benchmark.run_benchmark(db_session, repo)
    s = result["summary"]
    # every metric must stay within [0, 1] — the dedup + strict-match invariant
    for key in ("recall_at_1", "recall_at_5", "mrr", "map"):
        assert 0.0 <= s[key] <= 1.0, f"{key}={s[key]} out of range"


# ── Endpoint ─────────────────────────────────────────────────────


def test_evaluate_409_when_not_ready(client: TestClient, monkeypatch):
    monkeypatch.setattr(ingestion_service, "run_ingestion", lambda *a, **k: None)
    headers = _auth_headers(client)
    repo = client.post(
        "/api/repositories",
        json={"url": "https://github.com/pallets/itsdangerous"},
        headers=headers,
    ).json()
    assert (
        client.post(f"/api/repositories/{repo['id']}/evaluate", headers=headers).status_code == 409
    )


def test_evaluate_422_when_no_benchmark(client: TestClient, db_session: Session, monkeypatch):
    monkeypatch.setattr(ingestion_service, "run_ingestion", lambda *a, **k: None)
    headers = _auth_headers(client)
    created = client.post(
        "/api/repositories", json={"url": "https://github.com/pallets/flask"}, headers=headers
    ).json()
    repo = db_session.get(Repository, created["id"])
    repo.status = RepoStatus.ready
    db_session.commit()
    resp = client.post(f"/api/repositories/{created['id']}/evaluate", headers=headers)
    assert resp.status_code == 422  # "flask" has no benchmark entry


def test_evaluate_returns_metrics(client: TestClient, db_session: Session, monkeypatch):
    monkeypatch.setattr(ingestion_service, "run_ingestion", lambda *a, **k: None)
    headers = _auth_headers(client)
    created = client.post(
        "/api/repositories",
        json={"url": "https://github.com/pallets/itsdangerous"},
        headers=headers,
    ).json()
    repo = db_session.get(Repository, created["id"])
    repo.status = RepoStatus.ready
    db_session.commit()
    monkeypatch.setattr(
        search_service,
        "search_repository",
        lambda db, r, q, limit: [_hit("src/itsdangerous/signer.py")],
    )
    resp = client.post(f"/api/repositories/{created['id']}/evaluate", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["repo"] == "itsdangerous"
    assert body["summary"]["queries"] == 8
    assert len(body["per_query"]) == 8
