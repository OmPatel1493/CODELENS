"""Auth request/response schemas.

These define the API contract and are intentionally separate from the ORM models:
the DB model has a `hashed_password` we must never expose, and inbound data needs
its own validation (email format, password length). Schemas are that boundary.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRead(BaseModel):
    # from_attributes lets FastAPI serialize an ORM User directly into this schema.
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
