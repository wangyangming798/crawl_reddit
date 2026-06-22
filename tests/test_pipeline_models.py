from datetime import datetime, timezone
from pipeline.models import PostMetrics, CommentMetrics, CommonPost, CommonComment


def test_post_metrics_defaults():
    m = PostMetrics()
    assert m.upvotes == 0
    assert m.comment_count == 0


def test_post_metrics_custom():
    m = PostMetrics(upvotes=42, comment_count=7)
    assert m.upvotes == 42
    assert m.comment_count == 7


def test_comment_metrics_defaults():
    m = CommentMetrics()
    assert m.upvotes == 0


def test_common_post_creation():
    now = datetime(2026, 6, 15, tzinfo=timezone.utc)
    post = CommonPost(
        platform="reddit",
        post_id="abc123",
        title="This moisturizer broke me out",
        body="I've been using it for 2 weeks...",
        author_id="user456",
        created_at=now,
        country="us",
        sub_community="r/SkincareAddiction",
        metrics=PostMetrics(upvotes=230, comment_count=45),
        raw_json={"original_field": "value"},
    )

    assert post.platform == "reddit"
    assert post.post_id == "abc123"
    assert post.title == "This moisturizer broke me out"
    assert post.author_id == "user456"
    assert post.sub_community == "r/SkincareAddiction"
    assert post.country == "us"
    assert post.metrics.upvotes == 230
    assert post.raw_json == {"original_field": "value"}


def test_common_comment_creation():
    now = datetime(2026, 6, 15, tzinfo=timezone.utc)
    comment = CommonComment(
        platform="reddit",
        comment_id="c789",
        post_id="abc123",
        body="Same thing happened to me!",
        author_id="user999",
        parent_id=None,
        created_at=now,
        metrics=CommentMetrics(upvotes=15),
        raw_json={},
    )

    assert comment.comment_id == "c789"
    assert comment.post_id == "abc123"
    assert comment.parent_id is None
    assert comment.body == "Same thing happened to me!"


def test_common_comment_with_parent():
    comment = CommonComment(
        platform="reddit",
        comment_id="c790",
        post_id="abc123",
        body="Reply to parent",
        author_id="user888",
        parent_id="c789",
        created_at=datetime(2026, 6, 15, tzinfo=timezone.utc),
        metrics=CommentMetrics(),
        raw_json={},
    )
    assert comment.parent_id == "c789"