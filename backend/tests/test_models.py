"""ORM model tests: persistence, relationships, enums, and cascade delete."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    ChunkKind,
    CodeChunk,
    Repository,
    RepoSource,
    RepoStatus,
    User,
)


def _make_user(db: Session, email: str = "dev@codelens.test") -> User:
    user = User(email=email, hashed_password="not-a-real-hash")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_user_persists_with_defaults(db_session: Session):
    user = _make_user(db_session)
    assert user.id is not None
    assert user.created_at is not None  # server default populated


def test_repository_defaults_to_pending(db_session: Session):
    user = _make_user(db_session)
    repo = Repository(owner_id=user.id, name="demo", source=RepoSource.github)
    db_session.add(repo)
    db_session.commit()
    db_session.refresh(repo)
    assert repo.status is RepoStatus.pending  # default applied


def test_relationships_link_user_repo_chunk(db_session: Session):
    user = _make_user(db_session)
    repo = Repository(owner_id=user.id, name="demo", source=RepoSource.upload)
    repo.chunks.append(
        CodeChunk(
            file_path="app/auth.py",
            symbol_name="verify_token",
            kind=ChunkKind.function,
            start_line=10,
            end_line=25,
            content="def verify_token(...): ...",
        )
    )
    user.repositories.append(repo)
    db_session.commit()

    loaded = db_session.scalar(select(User).where(User.id == user.id))
    assert loaded is not None
    assert len(loaded.repositories) == 1
    assert loaded.repositories[0].chunks[0].symbol_name == "verify_token"


def test_cascade_delete_removes_children(db_session: Session):
    user = _make_user(db_session)
    repo = Repository(owner_id=user.id, name="demo", source=RepoSource.github)
    repo.chunks.append(
        CodeChunk(
            file_path="main.py",
            kind=ChunkKind.file,
            start_line=1,
            end_line=100,
            content="...",
        )
    )
    user.repositories.append(repo)
    db_session.commit()

    db_session.delete(user)
    db_session.commit()

    assert db_session.scalar(select(Repository)) is None
    assert db_session.scalar(select(CodeChunk)) is None
