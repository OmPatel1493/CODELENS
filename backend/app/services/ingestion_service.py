"""Repository ingestion: create the record, archive the source, count files.

Ingestion runs in two parts:
1. Synchronous (in the request): create the `Repository` row as `pending`.
2. Background (after the response): archive the source into storage, count files,
   and flip status to `ready` (or `failed`). We use FastAPI BackgroundTasks — free
   and in-process; a real queue (Celery/RQ) is a later scaling step.

The heavy helpers are pure functions so they unit-test without a server or network.
"""

from __future__ import annotations

import io
import re
import tarfile
import zipfile

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.repository import Repository, RepoSource, RepoStatus
from app.services.storage import StorageBackend, get_storage

_GITHUB_URL = re.compile(
    r"^(?:https?://)?(?:www\.)?github\.com/(?P<owner>[\w.-]+)/(?P<repo>[\w.-]+?)(?:\.git)?/?$"
)


def parse_github_url(url: str) -> tuple[str, str]:
    """Return (owner, repo) from a GitHub URL, or raise ValueError."""
    match = _GITHUB_URL.match(url.strip())
    if not match:
        raise ValueError("Not a valid GitHub repository URL")
    return match.group("owner"), match.group("repo")


def download_github_tarball(owner: str, repo: str) -> bytes:
    """Download the default-branch tarball of a public GitHub repo.

    Uses the unauthenticated tarball endpoint (redirects to the archive). Enforces
    the size guardrail while streaming so a huge repo can't exhaust memory.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/tarball"
    buffer = io.BytesIO()
    with httpx.Client(follow_redirects=True, timeout=60) as client:
        with client.stream("GET", url, headers={"Accept": "application/vnd.github+json"}) as resp:
            if resp.status_code == 404:
                raise ValueError("Repository not found or is private")
            resp.raise_for_status()
            for chunk in resp.iter_bytes():
                buffer.write(chunk)
                if buffer.tell() > settings.MAX_ARCHIVE_BYTES:
                    raise ValueError("Repository archive exceeds the size limit")
    return buffer.getvalue()


def count_files_in_zip(data: bytes) -> int:
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        return sum(1 for name in zf.namelist() if not name.endswith("/"))


def count_files_in_tarball(data: bytes) -> int:
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
        return sum(1 for member in tf.getmembers() if member.isfile())


def count_files(data: bytes, ext: str) -> int:
    return count_files_in_zip(data) if ext == "zip" else count_files_in_tarball(data)


def create_repository(
    db: Session,
    owner_id: int,
    name: str,
    source: RepoSource,
    source_url: str | None = None,
) -> Repository:
    """Create a `pending` repository record (synchronous part of ingestion)."""
    repo = Repository(owner_id=owner_id, name=name, source=source, source_url=source_url)
    db.add(repo)
    db.commit()
    db.refresh(repo)
    return repo


def process_repository_archive(
    db: Session,
    storage: StorageBackend,
    repo: Repository,
    archive_bytes: bytes,
    ext: str,
) -> None:
    """Store the archive, count files, mark ready. Pure w.r.t. its dependencies."""
    key = f"repositories/{repo.id}/source.{ext}"
    storage.save_bytes(key, archive_bytes)
    repo.archive_key = key
    repo.file_count = count_files(archive_bytes, ext)
    repo.status = RepoStatus.ready
    db.commit()


def run_ingestion(repo_id: int, upload_bytes: bytes | None = None) -> None:
    """Background entry point: archive + count + finalize status.

    Opens its own DB session because it runs after the request session is closed.
    On any failure the repo is marked `failed` with the reason recorded.
    """
    db = SessionLocal()
    storage = get_storage()
    repo = db.get(Repository, repo_id)
    if repo is None:
        db.close()
        return
    try:
        repo.status = RepoStatus.indexing
        db.commit()

        if repo.source is RepoSource.github:
            owner, name = parse_github_url(repo.source_url or "")
            archive_bytes, ext = download_github_tarball(owner, name), "tar.gz"
        else:
            if upload_bytes is None:
                raise ValueError("No uploaded archive provided")
            archive_bytes, ext = upload_bytes, "zip"

        process_repository_archive(db, storage, repo, archive_bytes, ext)
    except Exception as exc:  # noqa: BLE001 — record any failure for the user
        repo.status = RepoStatus.failed
        repo.error_message = str(exc)
        db.commit()
    finally:
        db.close()
