"""Rank the source files most likely responsible for an error.

Strategy: embed the parsed error text and retrieve candidate chunks from the vector
index, then aggregate hits by file. Files the trace *names directly* (by filename or
by a function in a frame) get a score boost and an explicit explanation — those are
the strongest signals. Each result carries a human-readable reason so the ranking is
transparent, not a black box.
"""

from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.models.code_chunk import CodeChunk
from app.models.repository import Repository
from app.schemas.bug import LocalizedFile, ParsedLogOut
from app.services import embedder, log_parser, vector_store

_FILE_BOOST = 0.3
_SYMBOL_BOOST = 0.2
_SNIPPET_MAX_LINES = 30


def _basename(path: str) -> str:
    return re.split(r"[/\\]", path)[-1]


def _snippet(content: str) -> str:
    return "\n".join(content.splitlines()[:_SNIPPET_MAX_LINES])


def localize(
    db: Session, repo: Repository, log_text: str, limit: int
) -> tuple[ParsedLogOut, list[LocalizedFile]]:
    parsed = log_parser.parse_log(log_text)
    query_vector = embedder.embed_query(parsed.query_text)
    # Over-fetch so per-file aggregation has enough material.
    raw_hits = vector_store.query(repo.id, query_vector, n_results=max(limit * 4, 12))

    named_files = {_basename(f).lower() for f in parsed.files}
    named_symbols = {s.lower() for s in parsed.symbols}

    # Aggregate chunk hits into per-file candidates, keeping the best-matching chunk.
    by_file: dict[str, dict] = {}
    for hit in raw_hits:
        chunk = db.get(CodeChunk, int(hit["id"]))
        if chunk is None:
            continue
        base = max(0.0, min(1.0, 1.0 - (hit.get("distance") or 0.0)))
        entry = by_file.setdefault(chunk.file_path, {"base": 0.0, "symbols": set(), "best": chunk})
        if base > entry["base"]:
            entry["base"] = base
            entry["best"] = chunk
        if chunk.symbol_name:
            entry["symbols"].add(chunk.symbol_name)

    results: list[LocalizedFile] = []
    for path, entry in by_file.items():
        score = entry["base"]
        reasons: list[str] = []

        file_named = _basename(path).lower() in named_files
        matched_symbols = sorted(s for s in entry["symbols"] if s.lower() in named_symbols)

        if file_named:
            score += _FILE_BOOST
            reasons.append("named directly in the stack trace")
        if matched_symbols:
            score += _SYMBOL_BOOST
            reasons.append(f"defines {', '.join(matched_symbols)} from the trace")
        if entry["base"] > 0 and not reasons:
            reasons.append("semantically related to the error")
        elif entry["base"] > 0:
            reasons.append("and is semantically related to the error")

        best = entry["best"]
        results.append(
            LocalizedFile(
                file_path=path,
                score=round(min(1.0, score), 4),
                reason="; ".join(reasons).capitalize() or "Related to the error",
                matched_symbols=matched_symbols,
                snippet=_snippet(best.content),
                start_line=best.start_line,
                end_line=best.end_line,
            )
        )

    results.sort(key=lambda r: r.score, reverse=True)
    parsed_out = ParsedLogOut(
        error_type=parsed.error_type,
        message=parsed.message,
        files=parsed.files,
        symbols=parsed.symbols,
    )
    return parsed_out, results[:limit]
