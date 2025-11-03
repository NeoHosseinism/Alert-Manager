"""
Database connection and session management with async SQLAlchemy 2.0
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool, QueuePool

from monitoring_system.config import settings
from monitoring_system.config.logging import get_logger

log = get_logger(__name__)

# Global engine and session factory
_engine: AsyncEngine = None
_async_session_factory: async_sessionmaker = None


def create_engine() -> AsyncEngine:
    """
    Create async database engine

    Returns:
        AsyncEngine instance
    """
    # Choose pool class based on environment
    if settings.is_dev:
        poolclass = NullPool  # No pooling in dev for easier debugging
    else:
        poolclass = QueuePool

    engine = create_async_engine(
        settings.database_url,
        echo=settings.database_echo,
        poolclass=poolclass,
        pool_size=settings.database_pool_size if not settings.is_dev else 0,
        max_overflow=settings.database_max_overflow if not settings.is_dev else 0,
        pool_recycle=settings.database_pool_recycle,
        pool_pre_ping=True,  # Verify connections before using
        future=True,
    )

    log.info(
        "database_engine_created",
        pool_size=settings.database_pool_size if not settings.is_dev else 0,
        max_overflow=settings.database_max_overflow if not settings.is_dev else 0,
        environment=settings.environment,
    )

    return engine


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker:
    """
    Create session factory

    Args:
        engine: Database engine

    Returns:
        Session factory
    """
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


async def init_database() -> None:
    """Initialize database connection"""
    global _engine, _async_session_factory

    if _engine is not None:
        log.warning("database_already_initialized")
        return

    _engine = create_engine()
    _async_session_factory = create_session_factory(_engine)

    log.info("database_initialized")


async def close_database() -> None:
    """Close database connections"""
    global _engine, _async_session_factory

    if _engine is None:
        return

    await _engine.dispose()
    _engine = None
    _async_session_factory = None

    log.info("database_closed")


def get_session_factory() -> async_sessionmaker:
    """
    Get session factory

    Returns:
        Session factory

    Raises:
        RuntimeError: If database not initialized
    """
    if _async_session_factory is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return _async_session_factory


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session context manager

    Yields:
        AsyncSession instance

    Usage:
        async with get_session() as session:
            # Use session
            result = await session.execute(query)
    """
    session_factory = get_session_factory()
    session = session_factory()

    try:
        yield session
        await session.commit()
    except Exception as e:
        await session.rollback()
        log.error("database_session_error", error=str(e))
        raise
    finally:
        await session.close()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting database session (for dependency injection)

    Yields:
        AsyncSession instance
    """
    async with get_session() as session:
        yield session
