"""
Pytest configuration and fixtures
"""
import pytest
import asyncio
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from models.base import Base
from config import settings


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine"""
    # Use in-memory SQLite for testing
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session"""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
def sample_user_data():
    """Sample user data for testing"""
    return {
        "phone_number": "+989123456789",
        "role": "viewer",
        "telegram_user_id": 123456789,
        "telegram_username": "testuser",
        "is_active": True,
    }


@pytest.fixture
def sample_service_data():
    """Sample service data for testing"""
    return {
        "name": "test-service",
        "service_type": "health_check",
        "endpoint_url": "https://example.com/health",
        "expected_status_code": 200,
        "timeout_seconds": 10,
        "check_interval_seconds": 300,
        "max_retries": 3,
        "retry_delay_seconds": 30,
        "is_active": True,
        "environment": "dev",
    }
