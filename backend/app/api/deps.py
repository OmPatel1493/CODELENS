"""Shared FastAPI dependencies (injected into route signatures)."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User
from app.services import auth_service
from app.services.storage import StorageBackend, get_storage

# Request-scoped DB session.
DbSession = Annotated[Session, Depends(get_db)]

# Configured object-storage backend (local or S3).
StorageDep = Annotated[StorageBackend, Depends(get_storage)]

# Reads the `Authorization: Bearer <token>` header. `tokenUrl` powers Swagger's
# "Authorize" button and documents where clients obtain a token.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

_credentials_error = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: DbSession,
) -> User:
    """Resolve the authenticated user from the bearer token, or raise 401."""
    subject = decode_access_token(token)
    if subject is None:
        raise _credentials_error
    try:
        user_id = int(subject)
    except ValueError:
        raise _credentials_error from None
    user = auth_service.get_user_by_id(db, user_id)
    if user is None:
        raise _credentials_error
    return user


# Convenience alias for protected routes: `user: CurrentUser`.
CurrentUser = Annotated[User, Depends(get_current_user)]
