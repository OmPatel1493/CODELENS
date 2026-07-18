"""Authentication routes: register, login, and the current-user endpoint."""

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.core.security import create_access_token
from app.schemas.auth import Token, UserCreate, UserLogin, UserRead
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: DbSession) -> UserRead:
    if auth_service.get_user_by_email(db, payload.email) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )
    user = auth_service.create_user(db, payload.email, payload.password)
    return UserRead.model_validate(user)


@router.post("/login", response_model=Token)
def login(payload: UserLogin, db: DbSession) -> Token:
    user = auth_service.authenticate_user(db, payload.email, payload.password)
    if user is None:
        # Same message for "no such email" and "wrong password" — don't leak
        # which emails are registered.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    return Token(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserRead)
def read_me(current_user: CurrentUser) -> UserRead:
    return UserRead.model_validate(current_user)
