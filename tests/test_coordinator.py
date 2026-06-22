import pytest
from unittest.mock import AsyncMock, MagicMock
from crawler.coordinator import CrawlCoordinator, CrawlResult
from crawler.base import SearchQuery, RawPost, RawComment


@pytest.fixture
def mock_adapter():
    adapter = MagicMock()
    adapter.platform = "reddit"
    adapter.search_posts = AsyncMock(return_value=[
        RawPost(
            post_id="p1", title="T1", body="B1", author_id="a1",
            created_at=1.0, sub_community="r/test", upvotes=10, comment_count=1,
            url="http://x", raw_json={},
        ),
        RawPost(
            post_id="p2", title="T2", body="B2", author_id="a2",
            created_at=2.0, sub_community="r/test", upvotes=20, comment_count=2,
            url="http://y", raw_json={},
        ),
    ])

    async def get_comments_side_effect(post_id):
        mapping = {
            "p1": [RawComment(comment_id="c1", post_id="p1", body="C1", author_id="a3", created_at=3.0, raw_json={})],
            "p2": [RawComment(comment_id="c2", post_id="p2", body="C2", author_id="a4", created_at=4.0, raw_json={})],
        }
        return mapping.get(post_id, [])

    adapter.get_comments = AsyncMock(side_effect=get_comments_side_effect)
    return adapter


@pytest.fixture
def coordinator(mock_adapter):
    return CrawlCoordinator(adapters={"reddit": mock_adapter})


@pytest.mark.asyncio
async def test_run_crawl_basic(coordinator):
    """Full crawl cycle returns expected result."""
    query = SearchQuery(subreddits=["r/test"], country="us")

    result = await coordinator.run_crawl(query, platform="reddit")

    assert isinstance(result, CrawlResult)
    assert len(result.posts) == 2
    assert len(result.comments) == 2  # 1 comment per post
    assert result.total_posts == 2
    assert result.total_comments == 2
    assert result.platform == "reddit"


@pytest.mark.asyncio
async def test_run_crawl_multiple_subreddits_concurrent(coordinator, mock_adapter):
    """Multiple subreddits are crawled concurrently."""
    query = SearchQuery(subreddits=["r/test", "r/other"], country="us")

    result = await coordinator.run_crawl(query, platform="reddit")

    # search_posts called once per subreddit
    assert mock_adapter.search_posts.call_count == 2


@pytest.mark.asyncio
async def test_run_crawl_unknown_platform(coordinator):
    """Unknown platform raises ValueError."""
    query = SearchQuery(subreddits=["r/test"])

    with pytest.raises(ValueError, match="Unknown platform"):
        await coordinator.run_crawl(query, platform="unknown")


@pytest.mark.asyncio
async def test_run_crawl_deduplicates_posts(coordinator, mock_adapter):
    """Duplicate posts across subreddits are deduplicated."""
    mock_adapter.search_posts = AsyncMock(return_value=[
        RawPost(post_id="p1", title="T1", body="", author_id="a1", created_at=1.0, sub_community="r/test", raw_json={}),
        RawPost(post_id="p1", title="T1 dup", body="", author_id="a1", created_at=1.0, sub_community="r/other", raw_json={}),
    ])

    query = SearchQuery(subreddits=["r/test", "r/other"])
    result = await coordinator.run_crawl(query, platform="reddit")

    assert len(result.posts) == 1