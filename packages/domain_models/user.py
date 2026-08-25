"""User domain models."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlmodel import Column, DateTime, SQLModel
from sqlmodel import Field as SQLField


class UserRole(StrEnum):
    """User role enumeration."""

    ADMIN = "admin"
    DEVELOPER = "developer"
    APPROVER = "approver"
    VIEWER = "viewer"


class UserBase(SQLModel):
    """Base user model."""

    email: str = SQLField(unique=True, index=True, max_length=255)
    full_name: str = SQLField(max_length=255)
    role: UserRole = SQLField(default=UserRole.VIEWER)
    is_active: bool = SQLField(default=True)


class User(UserBase, table=True):
    """User entity stored in database."""

    id: UUID = SQLField(default_factory=uuid4, primary_key=True)
    hashed_password: str = SQLField(max_length=255)
    created_at: datetime = SQLField(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = SQLField(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=datetime.utcnow),
    )


class UserCreate(UserBase):
    """Model for creating a new user."""

    password: str = SQLField(min_length=8)


class UserRead(UserBase):
    """Public user representation. Never exposes the password hash."""

    id: UUID
    created_at: datetime
    updated_at: datetime
