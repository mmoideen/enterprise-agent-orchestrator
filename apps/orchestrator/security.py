"""Security utilities for authentication and authorization."""

import base64
import hashlib
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from apps.orchestrator.config import settings
from apps.orchestrator.database import get_session
from packages.domain_models.user import User, UserRole

security = HTTPBearer()

# bcrypt only consumes the first 72 bytes of input; longer passwords are
# pre-hashed so no entropy is silently discarded.
BCRYPT_MAX_BYTES = 72


def _password_bytes(password: str) -> bytes:
    """Encode a password for bcrypt, pre-hashing anything over the 72-byte limit."""
    encoded = password.encode()
    if len(encoded) > BCRYPT_MAX_BYTES:
        return base64.b64encode(hashlib.sha256(encoded).digest())
    return encoded


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password.

    Returns:
        Hashed password.
    """
    return bcrypt.hashpw(_password_bytes(password), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        plain_password: Plain text password.
        hashed_password: Hashed password.

    Returns:
        True if password matches, False otherwise.
    """
    return bcrypt.checkpw(_password_bytes(plain_password), hashed_password.encode())


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: Data to encode in the token.
        expires_delta: Optional custom expiration time.

    Returns:
        Encoded JWT token.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode.update({"exp": expire})
    encoded_jwt: str = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session),
) -> User:
    """
    Dependency for getting the current authenticated user.

    Args:
        credentials: HTTP bearer token credentials.
        session: Database session.

    Returns:
        Current authenticated user.

    Raises:
        HTTPException: If authentication fails.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        subject = UUID(user_id)
    except (JWTError, ValueError):
        raise credentials_exception from None

    result = await session.execute(select(User).where(User.id == subject))
    user: User | None = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    return user


def require_role(*required_roles: UserRole) -> Callable[..., Awaitable[User]]:
    """
    Build a dependency that authenticates the caller and enforces its role.

    Args:
        required_roles: Roles that are allowed to call the endpoint.

    Returns:
        A FastAPI dependency resolving to the authorized user.
    """

    async def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions. Required roles: "
                + ", ".join(role.value for role in required_roles),
            )
        return current_user

    return dependency
