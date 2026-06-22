import pytest
from sqlalchemy import select
from writer.batch import BatchWriter
from writer.db import Platform, Post, Comment


@pytest.fixture
async def batch_writer(test_session):
    """Create a BatchWriter with a test session."""
    # Ensure platform exists
    platform = Platform(name="reddit")
    test_session.add(platform)
    await test_session.commit()

    return BatchWriter(test_session)


@pytest.mark.asyncio
async def test_insert_posts(batch_writer, test_session):
    """Batch insert posts and verify they're stored."""
    from datetime import datetime, timezone

    posts = [
        Post(
            platform_id=1,
            post_id="p1",
            title="Post 1",
            body="Body 1",
            author_id="a1",
            sub_community="r/test",
            country_code="us",
            created_at_utc=datetime(2026, 6, 15, tzinfo=timezone.utc),
            raw_json={"key": "v1"},
        ),
        Post(
            platform_id=1,
            post_id="p2",
            title="Post 2",
            body="Body 2",
            author_id="a2",
            sub_community="r/test",
            country_code="us",
            created_at_utc=datetime(2026, 6, 14, tzinfo=timezone.utc),
            raw_json={"key": "v2"},
        ),
    ]

    await batch_writer.insert_posts(posts)

    result = await test_session.execute(select(Post).order_by(Post.post_id))
    rows = result.scalars().all()
    assert len(rows) == 2
    assert rows[0].title == "Post 1"
    assert rows[1].title == "Post 2"


@pytest.mark.asyncio
async def test_insert_posts_skip_duplicates(batch_writer, test_session):
    """Duplicate posts are silently skipped."""
    from datetime import datetime, timezone

    post1 = Post(
        platform_id=1,
        post_id="dup1",
        title="First",
        body="Body",
        author_id="a1",
        sub_community="r/test",
        country_code="us",
        created_at_utc=datetime(2026, 6, 15, tzinfo=timezone.utc),
        raw_json={},
    )
    post2 = Post(
        platform_id=1,
        post_id="dup1",
        title="Second (dup)",
        body="Body 2",
        author_id="a1",
        sub_community="r/test",
        country_code="us",
        created_at_utc=datetime(2026, 6, 15, tzinfo=timezone.utc),
        raw_json={},
    )

    await batch_writer.insert_posts([post1])
    await batch_writer.insert_posts([post2])  # Should not raise

    result = await test_session.execute(
        select(Post).where(Post.post_id == "dup1")
    )
    rows = result.scalars().all()
    assert len(rows) == 1
    assert rows[0].title == "First"  # Original kept, duplicate skipped


@pytest.mark.asyncio
async def test_insert_comments(batch_writer, test_session):
    """Batch insert comments."""
    from datetime import datetime, timezone

    comments = [
        Comment(
            platform_id=1,
            comment_id="c1",
            post_id="p1",
            body="Comment 1",
            author_id="a1",
            created_at_utc=datetime(2026, 6, 15, tzinfo=timezone.utc),
            raw_json={},
        ),
        Comment(
            platform_id=1,
            comment_id="c2",
            post_id="p1",
            body="Comment 2",
            author_id="a2",
            created_at_utc=datetime(2026, 6, 15, tzinfo=timezone.utc),
            raw_json={},
        ),
    ]

    await batch_writer.insert_comments(comments)

    result = await test_session.execute(select(Comment).order_by(Comment.comment_id))
    rows = result.scalars().all()
    assert len(rows) == 2


@pytest.mark.asyncio
async def test_upsert_platform(batch_writer, test_session):
    """upsert_platform inserts or gets existing platform."""
    # Get existing
    pid = await batch_writer.upsert_platform("reddit")
    assert pid == 1

    # Insert new
    pid2 = await batch_writer.upsert_platform("twitter")
    assert pid2 == 2