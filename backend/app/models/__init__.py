"""Model package.

Importing the models here ensures they're registered on `Base.metadata` (so
`create_all` / migrations see them) whenever `app.models` is imported.
"""

from app.models.code_chunk import ChunkKind, CodeChunk
from app.models.repository import Repository, RepoSource, RepoStatus
from app.models.user import User

__all__ = [
    "User",
    "Repository",
    "RepoSource",
    "RepoStatus",
    "CodeChunk",
    "ChunkKind",
]
