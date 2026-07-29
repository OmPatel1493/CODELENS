"""Retrieval-evaluation response schemas."""

from pydantic import BaseModel


class EvalSummary(BaseModel):
    queries: int
    recall_at_1: float
    recall_at_5: float
    mrr: float
    map: float


class EvalCase(BaseModel):
    query: str
    expected: list[str]
    # 1-based rank of the first relevant result; 0 = not found in the top-k.
    found_rank: int
    recall_at_1: float
    recall_at_5: float
    reciprocal_rank: float
    average_precision: float


class EvalResponse(BaseModel):
    repo: str
    summary: EvalSummary
    per_query: list[EvalCase]
