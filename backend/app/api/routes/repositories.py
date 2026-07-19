"""Repository ingestion routes.

Two ways in — a public GitHub URL, or a direct .zip upload — plus list/get/delete.
Ingestion returns immediately with a `pending`/`indexing` record; the archiving and
file-count happen in a background task that flips the status to `ready`/`failed`.
"""

from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession, StorageDep
from app.core.config import settings
from app.models.code_chunk import CodeChunk
from app.models.repository import Repository, RepoSource, RepoStatus
from app.models.search_log import SearchLog
from app.schemas.repository import GithubIngestRequest, RepositoryRead, RepoStats
from app.schemas.search import SearchRequest, SearchResponse
from app.services import ingestion_service, search_service

router = APIRouter(prefix="/repositories", tags=["repositories"])


def _get_owned_repo(db: DbSession, repo_id: int, user: CurrentUser) -> Repository:
    repo = db.get(Repository, repo_id)
    if repo is None or repo.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")
    return repo


@router.get("", response_model=list[RepositoryRead])
def list_repositories(db: DbSession, user: CurrentUser) -> list[Repository]:
    stmt = (
        select(Repository)
        .where(Repository.owner_id == user.id)
        .order_by(Repository.created_at.desc())
    )
    return list(db.scalars(stmt))


@router.get("/stats", response_model=RepoStats)
def repository_stats(db: DbSession, user: CurrentUser) -> RepoStats:
    """Aggregate counts for the current user (drives the dashboard)."""
    repo_count = db.scalar(
        select(func.count()).select_from(Repository).where(Repository.owner_id == user.id)
    )
    chunk_count = db.scalar(
        select(func.count())
        .select_from(CodeChunk)
        .join(Repository, CodeChunk.repository_id == Repository.id)
        .where(Repository.owner_id == user.id)
    )
    search_count = db.scalar(
        select(func.count())
        .select_from(SearchLog)
        .join(Repository, SearchLog.repository_id == Repository.id)
        .where(Repository.owner_id == user.id)
    )
    return RepoStats(
        repositories=repo_count or 0,
        indexed_chunks=chunk_count or 0,
        searches_run=search_count or 0,
    )


@router.get("/{repo_id}", response_model=RepositoryRead)
def get_repository(repo_id: int, db: DbSession, user: CurrentUser) -> Repository:
    return _get_owned_repo(db, repo_id, user)


@router.post("/{repo_id}/search", response_model=SearchResponse)
def search_repository(
    repo_id: int, payload: SearchRequest, db: DbSession, user: CurrentUser
) -> SearchResponse:
    repo = _get_owned_repo(db, repo_id, user)
    if repo.status is not RepoStatus.ready:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Repository is not indexed yet",
        )
    results = search_service.search_repository(db, repo, payload.query, payload.limit)
    return SearchResponse(query=payload.query, results=results)


@router.post("", response_model=RepositoryRead, status_code=status.HTTP_201_CREATED)
def ingest_github(
    payload: GithubIngestRequest,
    db: DbSession,
    user: CurrentUser,
    background: BackgroundTasks,
) -> Repository:
    try:
        _, name = ingestion_service.parse_github_url(payload.url)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc

    repo = ingestion_service.create_repository(
        db, user.id, name=name, source=RepoSource.github, source_url=payload.url
    )
    background.add_task(ingestion_service.run_ingestion, repo.id)
    return repo


@router.post("/upload", response_model=RepositoryRead, status_code=status.HTTP_201_CREATED)
async def ingest_upload(
    db: DbSession,
    user: CurrentUser,
    background: BackgroundTasks,
    name: Annotated[str, Form(min_length=1, max_length=255)],
    file: Annotated[UploadFile, File()],
) -> Repository:
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Upload must be a .zip archive",
        )
    data = await file.read()
    if len(data) > settings.MAX_ARCHIVE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Archive exceeds the size limit",
        )

    repo = ingestion_service.create_repository(db, user.id, name=name, source=RepoSource.upload)
    background.add_task(ingestion_service.run_ingestion, repo.id, data)
    return repo


@router.delete("/{repo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_repository(repo_id: int, db: DbSession, user: CurrentUser, storage: StorageDep) -> None:
    repo = _get_owned_repo(db, repo_id, user)
    if repo.archive_key:
        storage.delete(repo.archive_key)
    from app.services import vector_store

    vector_store.delete_repository_index(repo.id)
    db.delete(repo)
    db.commit()
