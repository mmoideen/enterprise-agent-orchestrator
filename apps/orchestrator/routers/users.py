"""User management and authentication endpoints."""

from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from apps.orchestrator.config import settings
from apps.orchestrator.database import get_session
from apps.orchestrator.security import (
    create_access_token,
    get_current_user,
    hash_password,
    require_role,
    verify_password,
)
from packages.domain_models.user import User, UserCreate, UserRead, UserRole


router = APIRouter(prefix="/users", tags=["users"])


class Token(BaseModel):
    """Authentication token response."""

    access_token: str
    token_type: str


class LoginRequest(BaseModel):
    """Login request body."""

    email: str
    password: str


async def _create_user(session: AsyncSession, user_data: UserCreate, role: UserRole) -> User:
    """Persist a new user with the given role, rejecting duplicate emails."""
    result = await session.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = User(
        email=user_data.email,
        full_name=user_data.full_name,
        role=role,
        is_active=user_data.is_active,
        hashed_password=hash_password(user_data.password),
    )

    session.add(user)
    await session.commit()
    await session.refresh(user)

    return user


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    session: AsyncSession = Depends(get_session),
) -> User:
    """
    Self-register a new user.

    Self-registration is unauthenticated, so the requested role is ignored and
    the account is always created as a viewer. Privileged accounts are created
    through the admin-only ``POST /users/`` endpoint.
    """
    return await _create_user(session, user_data, UserRole.VIEWER)


@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> User:
    """Create a user with an explicit role. Only accessible to administrators."""
    return await _create_user(session, user_data, user_data.role)


@router.post("/login", response_model=Token)
async def login(
    login_data: LoginRequest,
    session: AsyncSession = Depends(get_session),
) -> Token:
    """Authenticate a user and return an access token."""
    result = await session.execute(select(User).where(User.email == login_data.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )

    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )

    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserRead)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current authenticated user information."""
    return current_user


@router.get("/", response_model=list[UserRead])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> list[User]:
    """
    List all users.

    Only accessible to administrators.
    """
    query = select(User).offset(skip).limit(limit)
    result = await session.execute(query)
    users = result.scalars().all()

    return list(users)


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> User:
    """
    Get a specific user by ID.

    Only accessible to administrators.
    """
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user
