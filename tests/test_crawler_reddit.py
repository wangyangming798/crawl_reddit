import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from crawler.reddit.api import RedditAdapter
from crawler.base import SearchQuery


def _make_async_cm_response(status=200, json_data=None, headers=None):
    """Create a MagicMock that works as an async context manager (like an aiohttp response)."""
    resp = MagicMock()
    resp.status = status
    resp.headers = headers or {}
    resp.json = AsyncMock(return_value=json_data)
    resp.__aenter__ = AsyncMock(return_value=resp)
    resp.__aexit__ = AsyncMock(return_value=None)
    return resp


def _make_mock_session(get_return=None, post_return=None, get_side_effect=None):
    """Create a MagicMock session that works as an async context manager."""
    session = MagicMock()
    if get_side_effect is not None:
        session.get = MagicMock(side_effect=get_side_effect)
    else:
        session.get = MagicMock(return_value=get_return)
    session.post = MagicMock(return_value=post_return)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    return session


@pytest.fixture
def reddit_config():
    from config import RedditConfig
    return RedditConfig(
        client_id="test-cid",
        client_secret="test-secret",
        user_agent="test-ua/1.0",
    )


@pytest.fixture
def adapter(reddit_config):
    return RedditAdapter(reddit_config)


def test_adapter_platform_name(adapter):
    assert adapter.platform == "reddit"


@pytest.mark.asyncio
async def test_get_access_token(adapter):
    """verify we request token with correct params."""
    mock_resp = _make_async_cm_response(
        json_data={"access_token": "test-token", "expires_in": 3600}
    )
    mock_session = _make_mock_session(post_return=mock_resp)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        token = await adapter._get_access_token()

    assert token == "test-token"


@pytest.mark.asyncio
async def test_search_posts_by_subreddit(adapter):
    """search_posts with subreddits calls the subreddit endpoint."""
    adapter._access_token = "fake-token"
    adapter._token_expires_at = 99999999999

    mock_listing = {
        "data": {
            "children": [
                {
                    "data": {
                        "id": "abc123",
                        "title": "Test post",
                        "selftext": "Post body",
                        "author": "user1",
                        "created_utc": 1718400000,
                        "subreddit": "SkincareAddiction",
                        "ups": 42,
                        "num_comments": 5,
                        "permalink": "/r/SkincareAddiction/comments/abc123/test/",
                    }
                }
            ],
            "after": None,
        }
    }

    mock_resp = _make_async_cm_response(json_data=mock_listing)
    mock_session = _make_mock_session(get_return=mock_resp)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        results = await adapter.search_posts(
            SearchQuery(subreddits=["SkincareAddiction"], limit=10)
        )

    assert len(results) == 1
    assert results[0].post_id == "abc123"
    assert results[0].title == "Test post"
    assert results[0].body == "Post body"
    assert results[0].author_id == "[redacted]"
    assert results[0].sub_community == "r/SkincareAddiction"
    assert results[0].upvotes == 42
    assert results[0].comment_count == 5


@pytest.mark.asyncio
async def test_search_posts_by_keyword(adapter):
    """search_posts with keywords calls the search endpoint."""
    adapter._access_token = "fake-token"
    adapter._token_expires_at = 99999999999

    mock_search_result = {
        "data": {
            "children": [
                {
                    "data": {
                        "id": "kw1",
                        "title": "Keyword match",
                        "selftext": "Body with keyword",
                        "author": "user2",
                        "created_utc": 1718400000,
                        "subreddit": "AskAnAmerican",
                        "ups": 10,
                        "num_comments": 3,
                        "permalink": "/r/AskAnAmerican/comments/kw1/test/",
                    }
                }
            ],
            "after": None,
        }
    }

    mock_resp = _make_async_cm_response(json_data=mock_search_result)
    mock_session = _make_mock_session(get_return=mock_resp)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        results = await adapter.search_posts(
            SearchQuery(keywords=["broke out"], limit=10)
        )

    assert len(results) == 1
    assert results[0].post_id == "kw1"


@pytest.mark.asyncio
async def test_get_comments(adapter):
    """get_comments fetches comments for a post."""
    adapter._access_token = "fake-token"
    adapter._token_expires_at = 99999999999

    # Reddit /comments/{id} returns [post_listing, comment_listing]
    mock_comments = [
        {"data": {"children": []}},  # post listing (ignored)
        {
            "data": {
                "children": [
                    {
                        "kind": "t1",
                        "data": {
                            "id": "c1",
                            "body": "Great comment",
                            "author": "commenter1",
                            "created_utc": 1718400000,
                            "ups": 5,
                            "parent_id": "t3_abc123",
                        }
                    },
                    {
                        "kind": "t1",
                        "data": {
                            "id": "c2",
                            "body": "Reply to c1",
                            "author": "commenter2",
                            "created_utc": 1718400100,
                            "ups": 2,
                            "parent_id": "t1_c1",
                        }
                    },
                ]
            }
        }
    ]

    mock_resp = _make_async_cm_response(json_data=mock_comments)
    mock_session = _make_mock_session(get_return=mock_resp)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        results = await adapter.get_comments("abc123")

    assert len(results) == 2
    assert results[0].comment_id == "c1"
    assert results[0].body == "Great comment"
    assert results[0].parent_id == "abc123"  # t3_ prefix stripped
    assert results[1].comment_id == "c2"
    assert results[1].parent_id == "c1"  # t1_ prefix stripped


@pytest.mark.asyncio
async def test_rate_limit_handling(adapter):
    """When rate limited, adapter retries after backoff."""
    adapter._access_token = "fake-token"
    adapter._token_expires_at = 99999999999

    rate_limit_resp = _make_async_cm_response(status=429, headers={"Retry-After": "1"})
    success_resp = _make_async_cm_response(
        json_data={"data": {"children": []}}
    )

    mock_session = _make_mock_session(
        get_side_effect=[rate_limit_resp, success_resp]
    )

    with patch("aiohttp.ClientSession", return_value=mock_session):
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            results = await adapter.search_posts(
                SearchQuery(subreddits=["test"], limit=1)
            )

    assert mock_sleep.called
    assert results == []