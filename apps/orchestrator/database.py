"""Database connection and session management."""

from collections.abc import AsyncGenerator

from sqlmodel import create_engine
from sqlmodel.ext.asyncio.session import AsyncEngine, AsyncSession
from sqlalchemy.orm import sessionmaker

from apps.orchestrator.config import settings


# Create async engine
async_engine = AsyncEngine(
    create_engine(
        settings.database_url,
        echo=False,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
    )
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting database sessions.

    Yields:
        AsyncSession for database operations.
    """
    async_session = sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with async_session() as session:
        yield session
