"""Database session management for async SQLAlchemy.

Provides async session factory and context managers for database operations.
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.config.settings import Settings

# Global engine and session factory (initialized on startup)
engine: AsyncEngine | None = None
async_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_db(settings: Settings) -> None:
    """Initialize database engine and session factory.

    Args:
        settings: Application settings with database URL
    """
    global engine, async_session_factory

    engine = create_async_engine(
        settings.database_url,
        echo=settings.db_echo,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_pre_ping=True,
    )

    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


async def close_db() -> None:
    """Close database engine and cleanup connections."""
    global engine

    if engine:
        await engine.dispose()
        engine = None


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session with automatic commit/rollback.

    Usage:
        async with get_db_session() as session:
            result = await session.execute(query)
            # Session commits on success, rolls back on exception

    Yields:
        AsyncSession: Database session
    """
    if async_session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    session = async_session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database session.

    Usage:
        @router.get("/endpoint")
        async def endpoint(db: AsyncSession = Depends(get_db)):
            result = await db.execute(query)
            return result

    Yields:
        AsyncSession: Database session
    """
    async with get_db_session() as session:
        yield session
