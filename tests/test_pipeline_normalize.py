from datetime import datetime, timezone
from pipeline.normalize import (
    normalize_post, normalize_comment,
    platform_id_for_name,
)
from crawler.base import RawPost, RawComment
from pipeline.models import CommonPost, CommonComment


def test_normalize_post():
    raw = RawPost(
        post_id="abc123",
        title="Test post",
        body="Body content",
        author_id="user1",
        created_at=1718400000.0,
        sub_community="r/SkincareAddiction",
        upvotes=42,
        comment_count=7,
        url="https://reddit.com/r/SkincareAddiction/abc123",
        raw_json={"native": "data"},
    )

    result = normalize_post(raw, platform="reddit", country="us")

    assert isinstance(result, CommonPost)
    assert result.platform == "reddit"
    assert result.post_id == "abc123"
    assert result.title == "Test post"
    assert result.body == "Body content"
    assert result.author_id == "user1"
    assert result.sub_community == "r/SkincareAddiction"
    assert result.country == "us"
    assert result.metrics.upvotes == 42
    assert result.metrics.comment_count == 7
    assert result.raw_json == {"native": "data"}
    assert result.created_at == datetime(2024, 6, 14, 21, 20, tzinfo=timezone.utc)


def test_normalize_post_empty_body():
    raw = RawPost(
        post_id="p1",
        title="No body",
        body="",
        author_id="u1",
        created_at=1718400000.0,
        sub_community="r/test",
        url="",
        raw_json={},
    )
    result = normalize_post(raw, platform="reddit", country="uk")
    assert result.body == ""
    assert result.country == "uk"


def test_normalize_comment():
    raw = RawComment(
        comment_id="c789",
        post_id="abc123",
        body="Great point!",
        author_id="user2",
        parent_id="c788",
        created_at=1718400000.0,
        upvotes=15,
        raw_json={"native": "comment_data"},
    )

    result = normalize_comment(raw, platform="reddit")

    assert isinstance(result, CommonComment)
    assert result.platform == "reddit"
    assert result.comment_id == "c789"
    assert result.post_id == "abc123"
    assert result.parent_id == "c788"
    assert result.body == "Great point!"
    assert result.author_id == "user2"
    assert result.metrics.upvotes == 15
    assert result.raw_json == {"native": "comment_data"}


def test_normalize_comment_no_parent():
    raw = RawComment(
        comment_id="c1",
        post_id="p1",
        body="Top level",
        author_id="u1",
        created_at=0.0,
        parent_id=None,
        raw_json={},
    )
    result = normalize_comment(raw, platform="reddit")
    assert result.parent_id is None


def test_platform_id_for_name():
    assert platform_id_for_name("reddit") == 1
    assert platform_id_for_name("twitter") == 2
    assert platform_id_for_name("facebook") == 3
    assert platform_id_for_name("unknown") == 1  # Defaults to reddit