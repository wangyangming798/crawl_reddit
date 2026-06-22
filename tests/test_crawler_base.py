import pytest
from crawler.base import BaseAdapter, SearchQuery, RawPost, RawComment


def test_search_query_defaults():
    q = SearchQuery(subreddits=["r/test"])
    assert q.subreddits == ["r/test"]
    assert q.keywords == []
    assert q.country == "us"
    assert q.limit == 100


def test_search_query_full():
    q = SearchQuery(
        subreddits=["r/test", "r/other"],
        keywords=["broke", "worst"],
        country="uk",
        limit=50,
    )
    assert q.subreddits == ["r/test", "r/other"]
    assert q.keywords == ["broke", "worst"]
    assert q.country == "uk"
    assert q.limit == 50


def test_raw_post_fields():
    post = RawPost(
        post_id="p1",
        title="Title",
        body="Body text",
        author_id="a1",
        created_at=1234567890.0,
        sub_community="r/test",
        upvotes=10,
        comment_count=5,
        url="https://reddit.com/r/test/p1",
        raw_json={"key": "val"},
    )
    assert post.post_id == "p1"
    assert post.body == "Body text"
    assert post.upvotes == 10


def test_raw_comment_fields():
    comment = RawComment(
        comment_id="c1",
        post_id="p1",
        body="Comment body",
        author_id="a2",
        parent_id=None,
        created_at=1234567890.0,
        upvotes=3,
        raw_json={},
    )
    assert comment.comment_id == "c1"
    assert comment.parent_id is None


def test_raw_post_default_author():
    post = RawPost(
        post_id="p1",
        title="Title",
        body="Body text",
        created_at=1234567890.0,
        sub_community="r/test",
    )
    assert post.author_id == "[redacted]"


def test_base_adapter_cannot_instantiate():
    """BaseAdapter is abstract and cannot be instantiated directly."""
    with pytest.raises(TypeError):
        BaseAdapter()


def test_concrete_adapter_must_implement_all_methods():
    """Subclass must implement all abstract methods."""

    class IncompleteAdapter(BaseAdapter):
        platform = "test"

        async def search_posts(self, query):
            pass

        # Missing get_comments

    with pytest.raises(TypeError):
        IncompleteAdapter()