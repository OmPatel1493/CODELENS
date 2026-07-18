"""Security primitives: password hashing and JWT creation/verification.

Kept separate from business logic and HTTP so it's independently testable and
reusable. Hashing uses bcrypt (via pwdlib); tokens are signed JWTs (via PyJWT).
"""

from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.bcrypt import BcryptHasher

from app.core.config import settings

# bcrypt hasher. `.hash()` generates a per-password salt; `.verify()` is
# constant-time. Never store or log the plaintext password.
_password_hash = PasswordHash((BcryptHasher(),))


def hash_password(plain_password: str) -> str:
    return _password_hash.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _password_hash.verify(plain_password, hashed_password)


def create_access_token(subject: str | int) -> str:
    """Create a signed JWT whose `sub` claim identifies the user (their id)."""
    now = datetime.now(UTC)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(subject),
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> str | None:
    """Return the `sub` claim if the token is valid, else None.

    Returns None on any failure (bad signature, expired, malformed) so callers
    treat all invalid tokens uniformly as "unauthenticated".
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None
    return payload.get("sub")
