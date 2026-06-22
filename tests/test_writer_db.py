import pytest
from sqlalchemy import select
from writer.db import (
    Base, Platform, Country, ResearchTask,
    Post, Comment, get_engine, get_session,
)


@pytest.mark.asyncio
async def test_platform_model(test_session):
    """Can insert and query a platform."""
    p = Platform(name="reddit")
    test_session.add(p)
    await test_session.commit()

    result = await test_session.execute(select(Platform).where(Platform.name == "reddit"))
    row = result.scalar_one()
    assert row.name == "reddit"
    assert row.id is not None


@pytest.mark.asyncio
async def test_country_model(test_session):
    """Can insert and query a country."""
    c = Country(code="us", name="United States")
    test_session.add(c)
    await test_session.commit()

    result = await test_session.execute(select(Country).where(Country.code == "us"))
    row = result.scalar_one()
    assert row.name == "United States"


@pytest.mark.asyncio
async def test_research_task_model(test_session):
    """Can insert and query a research task."""
    import uuid
    task_id = uuid.uuid4()
    task = ResearchTask(
        task_id=str(task_id),
        natural_query="test query",
        countries=["us", "uk"],
        subreddits=["r/test"],
        keywords=["pain", "point"],
        status="pending",
    )
    test_session.add(task)
    await test_session.commit()

    result = await test_session.execute(
        select(ResearchTask).where(ResearchTask.task_id == str(task_id))
    )
    row = result.scalar_one()
    assert row.natural_query == "test query"
    assert row.countries == ["us", "uk"]
    assert row.status == "pending"


@pytest.mark.asyncio
async def test_post_model(test_session):
    """Can insert a post with platform FK."""
    from datetime import datetime, timezone

    platform = Platform(name="reddit")
    test_session.add(platform)
    await test_session.flush()

    post = Post(
        platform_id=platform.id,
        post_id="abc123",
        title="Test post",
        body="Post body",
        author_id="user1",
        sub_community="r/test",
        country_code="us",
        url="https://reddit.com/r/test/abc123",
        upvotes=42,
        comment_count=5,
        raw_json={"extra": "data"},
    )
    test_session.add(post)
    await test_session.commit()

    result = await test_session.execute(select(Post).where(Post.post_id == "abc123"))
    row = result.scalar_one()
    assert row.title == "Test post"
    assert row.raw_json == {"extra": "data"}


@pytest.mark.asyncio
async def test_post_unique_constraint(test_session):
    """Duplicate (platform_id, post_id) raises IntegrityError."""
    from sqlalchemy.exc import IntegrityError

    platform = Platform(name="reddit")
    test_session.add(platform)
    await test_session.flush()

    p1 = Post(platform_id=platform.id, post_id="dup123", title="First")
    test_session.add(p1)
    await test_session.commit()

    p2 = Post(platform_id=platform.id, post_id="dup123", title="Second")
    test_session.add(p2)
    with pytest.raises(IntegrityError):
        await test_session.commit()


@pytest.mark.asyncio
async def test_comment_model(test_session):
    """Can insert a comment."""
    platform = Platform(name="reddit")
    test_session.add(platform)
    await test_session.flush()

    comment = Comment(
        platform_id=platform.id,
        comment_id="c789",
        post_id="abc123",
        body="Comment text",
        author_id="user2",
        parent_id="c788",
        upvotes=10,
        raw_json={},
    )
    test_session.add(comment)
    await test_session.commit()

    result = await test_session.execute(
        select(Comment).where(Comment.comment_id == "c789")
    )
    row = result.scalar_one()
    assert row.body == "Comment text"
    assert row.parent_id == "c788"


@pytest.mark.asyncio
async def test_get_engine_returns_async_engine(mock_env):
    """get_engine returns an async engine."""
    from config import load_config
    config = load_config()
    engine = get_engine(config)
    assert engine is not None
    await engine.dispose()


@pytest.mark.asyncio
async def test_get_session_yields_session(mock_env):
    """get_session yields an AsyncSession."""
    from config import load_config
    config = load_config()
    async for session in get_session(config):
        assert session is not None
        break