"""Information-retrieval metrics — pure functions, no dependencies.

Operate on a ranked list of relevance flags (True = the item at that rank is a
relevant/expected result) plus the total number of relevant items for the query.
Kept dependency-free and pure so they're trivially unit-tested and reusable.
"""

from __future__ import annotations


def recall_at_k(ranked_relevance: list[bool], k: int, num_relevant: int) -> float:
    """Fraction of the relevant items that appear in the top-k results."""
    if num_relevant <= 0:
        return 0.0
    return sum(ranked_relevance[:k]) / num_relevant


def reciprocal_rank(ranked_relevance: list[bool]) -> float:
    """1 / (rank of the first relevant result), or 0 if none are relevant."""
    for i, hit in enumerate(ranked_relevance, start=1):
        if hit:
            return 1.0 / i
    return 0.0


def average_precision(ranked_relevance: list[bool], num_relevant: int) -> float:
    """Average of precision@rank at each relevant hit (standard AP)."""
    if num_relevant <= 0:
        return 0.0
    hits = 0
    precision_sum = 0.0
    for i, is_hit in enumerate(ranked_relevance, start=1):
        if is_hit:
            hits += 1
            precision_sum += hits / i
    return precision_sum / num_relevant


def aggregate(per_query: list[dict], ks: tuple[int, ...] = (1, 5)) -> dict:
    """Mean each metric across queries → the summary the dashboard shows."""
    n = len(per_query)
    if n == 0:
        return {"queries": 0, "mrr": 0.0, "map": 0.0, **{f"recall_at_{k}": 0.0 for k in ks}}
    out: dict[str, float | int] = {"queries": n}
    for k in ks:
        out[f"recall_at_{k}"] = round(sum(q[f"recall_at_{k}"] for q in per_query) / n, 4)
    out["mrr"] = round(sum(q["reciprocal_rank"] for q in per_query) / n, 4)
    out["map"] = round(sum(q["average_precision"] for q in per_query) / n, 4)
    return out
