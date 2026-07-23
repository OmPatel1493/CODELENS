"""AI code review — review a diff *in the context of the indexed codebase*.

Pipeline: resolve a unified diff (pasted, or fetched from a public GitHub PR URL) →
derive a query from the changed files/lines and retrieve related repo chunks → ask
the LLM for a structured, severity-tagged review grounded in that context.

The retrieval step is the differentiator: the model doesn't just see the diff, it
sees related code from the repo (callers, siblings, definitions), so the review is
informed by the codebase — not the diff in isolation.
"""

from __future__ import annotations

import json
import re

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.repository import Repository
from app.schemas.review import ReviewComment
from app.schemas.search import SearchHit
from app.services import answer_service, search_service

_PR_URL_RE = re.compile(r"github\.com/([^/]+)/([^/]+)/pull/(\d+)")

_SYSTEM_PROMPT = (
    "You are a senior software engineer doing a careful code review. Review the unified "
    "diff for correctness bugs, edge cases, security issues, and clear improvements, "
    "using the provided repository context (related code from the same codebase) to "
    "judge impact. Cite context snippets with [n] when relevant.\n\n"
    "Respond with a JSON object only, matching exactly:\n"
    '{"summary": "<one-line verdict>", "comments": [{"severity": '
    '"high|medium|low|nit", "file": "<path or null>", "line": <int or null>, '
    '"comment": "<specific, actionable feedback>"}]}\n\n'
    "Order comments most-severe first. If the change looks solid, return an empty "
    "comments array and a positive summary. Do not invent issues."
)


def parse_pr_url(url: str) -> tuple[str, str, int]:
    """Extract (owner, repo, pr_number) from a GitHub pull-request URL."""
    m = _PR_URL_RE.search(url)
    if not m:
        raise ValueError("Not a valid GitHub pull-request URL (…/owner/repo/pull/N).")
    owner, repo, number = m.group(1), m.group(2), int(m.group(3))
    return owner, repo.removesuffix(".git"), number


def fetch_pr_diff(owner: str, repo: str, number: int) -> str:
    """Fetch a PR's unified diff via the GitHub API (public repos, unauthenticated)."""
    import httpx

    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{number}"
    resp = httpx.get(
        url,
        headers={"Accept": "application/vnd.github.diff", "User-Agent": "codelens"},
        timeout=30.0,
        follow_redirects=True,
    )
    if resp.status_code == 404:
        raise ValueError("Pull request not found (is the repo public?).")
    resp.raise_for_status()
    return resp.text


def _query_from_diff(diff: str) -> str:
    """Build a retrieval query from a diff's changed files + a sample of added lines."""
    files = re.findall(r"^\+\+\+ b/(.+)$", diff, flags=re.MULTILINE)
    added = [
        ln[1:].strip()
        for ln in diff.splitlines()
        if ln.startswith("+") and not ln.startswith("+++") and ln[1:].strip()
    ]
    parts = []
    if files:
        parts.append("Changes to " + ", ".join(dict.fromkeys(files)))
    parts.extend(added[:30])
    return "\n".join(parts) or diff[:1000]


def _parse_review(raw: str) -> tuple[str, list[ReviewComment]]:
    """Parse the model's JSON review, defensively falling back to raw text."""
    try:
        data = json.loads(raw)
        summary = str(data.get("summary", "")).strip() or "Review complete."
        comments = [
            ReviewComment(
                severity=str(c.get("severity", "low")).lower(),
                file=c.get("file"),
                line=c.get("line") if isinstance(c.get("line"), int) else None,
                comment=str(c.get("comment", "")).strip(),
            )
            for c in data.get("comments", [])
            if str(c.get("comment", "")).strip()
        ]
        return summary, comments
    except (json.JSONDecodeError, AttributeError, TypeError):
        # Model didn't return clean JSON — surface its text as the summary.
        return raw.strip()[:2000], []


def review(
    db: Session, repo: Repository, *, diff: str | None, pr_url: str | None
) -> tuple[str, list[ReviewComment], list[SearchHit]]:
    """Run an AI review of a diff (given or fetched from a PR) against the repo."""
    if pr_url and pr_url.strip():
        owner, name, number = parse_pr_url(pr_url)
        diff = fetch_pr_diff(owner, name, number)

    if not diff or not diff.strip():
        raise ValueError("No diff to review.")
    if len(diff.encode("utf-8")) > settings.MAX_DIFF_BYTES:
        raise ValueError(
            f"Diff too large (> {settings.MAX_DIFF_BYTES // 1000} KB). Review a smaller change."
        )

    sources = search_service.search_repository(
        db, repo, _query_from_diff(diff), settings.RAG_CONTEXT_CHUNKS
    )
    context = answer_service._build_context(sources) if sources else "(no related code found)"
    user_prompt = f"Unified diff:\n```diff\n{diff}\n```\n\nRepository context:\n\n{context}"
    raw = answer_service.get_llm().complete(
        _SYSTEM_PROMPT, user_prompt, json_mode=True, max_tokens=1200
    )
    summary, comments = _parse_review(raw)
    return summary, comments, sources
