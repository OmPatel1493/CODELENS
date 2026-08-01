"""Plain-English code explainer for non-technical users.

Takes real code from the indexed repo (the whole project, or one file) and asks the
LLM to explain it in everyday language — no jargon, analogies where helpful, and any
unavoidable technical term defined in a glossary. Output is *structured*
(title/summary/sections/glossary) so the UI can render a clean explainer document
with the raw code hidden — the opposite of a developer tool.

Reuses the shared LLM backend (answer_service.get_llm) and the indexed chunks; no new
model, no new infra.
"""

from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.code_chunk import ChunkKind, CodeChunk
from app.models.repository import Repository
from app.schemas.explain import ExplainSection, GlossaryItem
from app.services import answer_service

# Files whose basename hints they're an entry point / core — surfaced first in the
# whole-repo overview so the model explains what matters, not a random utility.
_ENTRY_HINTS = (
    "main",
    "app",
    "index",
    "__init__",
    "cli",
    "server",
    "settings",
    "config",
    "routes",
    "views",
    "models",
    "api",
)

_MAX_FILES = 12
_MAX_CHARS = 9000
_PER_FILE_CHARS = 700

_SYSTEM_PROMPT = (
    "You are CodeLens, explaining software to a NON-TECHNICAL person with no "
    "programming background — imagine a curious manager or a student's parent. Using "
    "ONLY the code provided, explain in plain, everyday English:\n"
    "- Say WHAT it does and WHY it's useful, not how the code is written.\n"
    "- Avoid jargon. If a technical word is unavoidable, put it in the glossary with a "
    "simple one-line definition.\n"
    "- Use short paragraphs and everyday analogies where they help.\n"
    "- Be warm and encouraging; never condescending.\n\n"
    "Respond with a JSON object only, matching exactly:\n"
    '{"title": "<friendly title>", "summary": "<2-3 plain sentences>", '
    '"sections": [{"heading": "<plain heading>", "body": "<explanation>"}], '
    '"glossary": [{"term": "<term>", "definition": "<simple definition>"}]}\n'
    "Use 3-5 sections. Leave glossary empty if no jargon was needed."
)


def _priority(file_path: str) -> int:
    base = file_path.rsplit("/", 1)[-1].lower()
    return 0 if any(h in base for h in _ENTRY_HINTS) else 1


def _repo_context(db: Session, repo: Repository) -> str:
    """A representative snippet per file, entry-point files first, size-capped."""
    rows = db.scalars(
        select(CodeChunk).where(CodeChunk.repository_id == repo.id).order_by(CodeChunk.id)
    ).all()
    by_file: dict[str, str] = {}
    for row in rows:
        # Prefer the whole-file chunk; otherwise keep the first snippet seen per file.
        if row.file_path not in by_file or row.kind is ChunkKind.file:
            by_file[row.file_path] = row.content[:_PER_FILE_CHARS]

    files = sorted(by_file, key=lambda p: (_priority(p), p))[:_MAX_FILES]
    blocks, total = [], 0
    for path in files:
        block = f"### {path}\n{by_file[path]}"
        if total + len(block) > _MAX_CHARS:
            break
        blocks.append(block)
        total += len(block)
    return "\n\n".join(blocks)


def _file_context(db: Session, repo: Repository, file_path: str) -> str:
    rows = db.scalars(
        select(CodeChunk)
        .where(CodeChunk.repository_id == repo.id, CodeChunk.file_path == file_path)
        .order_by(CodeChunk.start_line)
    ).all()
    if not rows:
        raise ValueError(f"No indexed code found for '{file_path}'.")
    text = "\n\n".join(r.content for r in rows)
    return text[:_MAX_CHARS]


def explain(db: Session, repo: Repository, scope: str, file: str | None) -> dict:
    """Return a structured plain-English explanation of the repo or one file."""
    if scope == "file":
        context = _file_context(db, repo, file or "")
        target = f"the file `{file}`"
    else:
        context = _repo_context(db, repo)
        if not context:
            raise ValueError("This repository has no indexed code to explain.")
        target = f"the project `{repo.name}` (representative files below)"

    user_prompt = f"Explain {target} to a non-technical person.\n\nCode:\n{context}"
    raw = answer_service.get_llm().complete(
        _SYSTEM_PROMPT, user_prompt, json_mode=True, max_tokens=1400
    )
    return {"scope": scope, **_parse(raw)}


def _parse(raw: str) -> dict:
    """Parse the model's JSON explainer, defensively falling back to raw text."""
    try:
        data = json.loads(raw)
        sections = [
            ExplainSection(
                heading=str(s.get("heading", "")).strip(), body=str(s.get("body", "")).strip()
            )
            for s in data.get("sections", [])
            if str(s.get("body", "")).strip()
        ]
        glossary = [
            GlossaryItem(
                term=str(g.get("term", "")).strip(), definition=str(g.get("definition", "")).strip()
            )
            for g in data.get("glossary", [])
            if str(g.get("term", "")).strip()
        ]
        return {
            "title": str(data.get("title", "")).strip() or "Explanation",
            "summary": str(data.get("summary", "")).strip(),
            "sections": sections,
            "glossary": glossary,
        }
    except (json.JSONDecodeError, AttributeError, TypeError):
        return {
            "title": "Explanation",
            "summary": raw.strip()[:2000],
            "sections": [],
            "glossary": [],
        }
