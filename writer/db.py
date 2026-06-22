import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator

from sqlalchemy import (
    Column, Integer, String, Text, DateTime,
    ForeignKey, UniqueConstraint, JSON,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker, AsyncEngine


class Base(DeclarativeBase):
    pass


class Platform(Base):
    __tablename__ = "platforms"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Country(Base):
    __tablename__ = "countries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), unique=True, nullable=False)
    name = Column(String(100))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ResearchTask(Base):
    __tablename__ = "research_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    natural_query = Column(Text)
    countries = Column(JSON)
    subreddits = Column(JSON)
    keywords = Column(JSON)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    finished_at = Column(DateTime, nullable=True)


class Post(Base):
    __tablename__ = "posts"
    __table_args__ = (
        UniqueConstraint("platform_id", "post_id", name="uq_platform_post"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    platform_id = Column(Integer, ForeignKey("platforms.id"), nullable=False)
    post_id = Column(String(255), nullable=False)
    title = Column(Text, nullable=False)
    body = Column(Text)
    author_id = Column(String(255))
    sub_community = Column(String(255))
    country_code = Column(String(10))
    url = Column(Text)
    upvotes = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    created_at_utc = Column(DateTime)
    crawled_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    task_id = Column(String(36), ForeignKey("research_tasks.task_id"), nullable=True)
    raw_json = Column(JSON)


class Comment(Base):
    __tablename__ = "comments"
    __table_args__ = (
        UniqueConstraint("platform_id", "comment_id", name="uq_platform_comment"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    platform_id = Column(Integer, ForeignKey("platforms.id"), nullable=False)
    comment_id = Column(String(255), nullable=False)
    post_id = Column(String(255), nullable=False)
    parent_id = Column(String(255))
    body = Column(Text, nullable=False)
    author_id = Column(String(255))
    upvotes = Column(Integer, default=0)
    created_at_utc = Column(DateTime)
    crawled_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    task_id = Column(String(36), ForeignKey("research_tasks.task_id"), nullable=True)
    raw_json = Column(JSON)


def get_engine(config) -> AsyncEngine:
    """Create async SQLAlchemy engine from config."""
    return create_async_engine(config.db.url, echo=False)


async def get_session(config) -> AsyncGenerator[AsyncSession, None]:
    """Async generator yielding database sessions."""
    engine = get_engine(config)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    await engine.dispose()


async def init_db(config) -> None:
    """Create all tables if they don't exist."""
    engine = get_engine(config)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()