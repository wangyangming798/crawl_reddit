import asyncio
import pytest
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker


@pytest.fixture
def mock_env(monkeypatch):
    """Set up minimal env vars for tests."""
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    monkeypatch.setenv("REDDIT_CLIENT_ID", "test-cid")
    monkeypatch.setenv("REDDIT_CLIENT_SECRET", "test-secret")


@pytest.fixture
def test_db_url():
    """Use an in-memory SQLite for tests (via aiosqlite)."""
    return "sqlite+aiosqlite://"


@pytest.fixture
async def test_engine(test_db_url):
    """Create async engine for test database."""
    engine = create_async_engine(test_db_url, echo=False)
    yield engine
    await engine.dispose()


@pytest.fixture
async def test_session(test_engine):
    """Create tables and yield an async session."""
    from writer.db import Base

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)