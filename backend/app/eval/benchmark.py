"""Retrieval benchmark — labeled query → expected-file sets, scored live.

Ground truth is hand-labeled per repo (there's no free lunch for retrieval eval),
keyed by repo name. `run_benchmark` runs each query through the *real* search
pipeline against an indexed repo and scores it with the metrics in
`services/metrics.py`, so the numbers reflect the deployed retriever, not a mock.

A query is a hit at a rank if the result's file path contains any of the query's
expected substrings. Add a repo's entry here to benchmark it.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.repository import Repository
from app.services import metrics, search_service

# repo name → labeled queries. `expected` = file-path substrings that count as relevant.
BENCHMARKS: dict[str, list[dict]] = {
    "itsdangerous": [
        {"query": "how is a signature verified against a secret key", "expected": ["signer.py"]},
        {"query": "sign and serialize a python object to a token", "expected": ["serializer.py"]},
        {"query": "url-safe base64 serializer", "expected": ["url_safe.py"]},
        {"query": "signatures that expire after a set time", "expected": ["timed.py"]},
        {"query": "base64 encode and decode helper functions", "expected": ["encoding.py"]},
        {
            "query": "exception raised when a signature is invalid or tampered",
            "expected": ["exc.py"],
        },
        {"query": "derive a signing key from a secret", "expected": ["signer.py"]},
        {
            "query": "load and verify a signed value, rejecting bad ones",
            "expected": ["serializer.py"],
        },
    ],
}

_TOP_K = 10


def has_benchmark(repo: Repository) -> bool:
    return repo.name in BENCHMARKS


def _is_relevant(file_path: str, expected: list[str]) -> bool:
    """A file is relevant if its path ends with an expected basename.

    Suffix-match on "/<name>" (or exact) — not a loose substring — so an expected
    of "signer.py" matches "src/pkg/signer.py" but NOT "tests/test_signer.py".
    """
    return any(file_path == exp or file_path.endswith("/" + exp) for exp in expected)


def run_benchmark(db: Session, repo: Repository) -> dict:
    """Run the labeled query set for `repo` through search and score it."""
    cases = BENCHMARKS.get(repo.name)
    if not cases:
        raise ValueError(
            f"No benchmark defined for '{repo.name}'. Available: {', '.join(BENCHMARKS) or 'none'}."
        )

    per_query = []
    for case in cases:
        hits = search_service.search_repository(db, repo, case["query"], _TOP_K)
        expected = case["expected"]
        # This is file-level retrieval: collapse chunk hits to distinct files (first
        # occurrence) before scoring, so several chunks from one file don't count as
        # several hits (which would push recall/MAP above 1).
        ranked_files: list[str] = []
        for hit in hits:
            if hit.file_path not in ranked_files:
                ranked_files.append(hit.file_path)
        ranked_relevance = [_is_relevant(fp, expected) for fp in ranked_files]
        # rank of the first relevant file (for display), 0 = not found in top-k
        found_rank = next((i + 1 for i, r in enumerate(ranked_relevance) if r), 0)
        per_query.append(
            {
                "query": case["query"],
                "expected": expected,
                "found_rank": found_rank,
                "recall_at_1": metrics.recall_at_k(ranked_relevance, 1, len(expected)),
                "recall_at_5": metrics.recall_at_k(ranked_relevance, 5, len(expected)),
                "reciprocal_rank": metrics.reciprocal_rank(ranked_relevance),
                "average_precision": metrics.average_precision(ranked_relevance, len(expected)),
            }
        )

    summary = metrics.aggregate(per_query, ks=(1, 5))
    return {"repo": repo.name, "summary": summary, "per_query": per_query}
