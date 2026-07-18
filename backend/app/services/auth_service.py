"""Authentication business logic.

Framework-agnostic: these functions take a Session and plain values and know
nothing about HTTP. Routes translate their results into responses/errors. This
keeps the logic unit-testable without a web server.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def create_user(db: Session, email: str, password: str) -> User:
    """Create a user with a hashed password. Caller must ensure email is free."""
    user = User(email=email, hashed_password=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    """Return the user if email exists and the password matches, else None."""
    user = get_user_by_email(db, email)
    if user is None:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user
