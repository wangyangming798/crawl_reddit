import asyncio
import logging
import time

import aiohttp

from config import RedditConfig
from crawler.base import BaseAdapter, SearchQuery, RawPost, RawComment

logger = logging.getLogger(__name__)

REDDIT_API_BASE = "https://oauth.reddit.com"
REDDIT_AUTH_URL = "https://www.reddit.com/api/v1/access_token"


class RedditAdapter(BaseAdapter):
    """Reddit official API adapter."""

    platform = "reddit"

    def __init__(self, config: RedditConfig):
        self.config = config
        self._access_token: str | None = None
        self._token_expires_at: float = 0

    async def _get_access_token(self) -> str:
        """Get or refresh OAuth2 access token."""
        if self._access_token and time.time() < self._token_expires_at - 60:
            return self._access_token

        auth = aiohttp.BasicAuth(self.config.client_id, self.config.client_secret)
        data = {"grant_type": "client_credentials"}

        async with aiohttp.ClientSession() as session:
            async with session.post(
                REDDIT_AUTH_URL,
                auth=auth,
                data=data,
                headers={"User-Agent": self.config.user_agent},
            ) as resp:
                resp.raise_for_status()
                body = await resp.json()
                self._access_token = body["access_token"]
                self._token_expires_at = time.time() + body.get("expires_in", 3600)
                return self._access_token

    async def _request(self, endpoint: str, params: dict | None = None) -> dict:
        """Make an authenticated GET request to the Reddit API with retry logic."""
        token = await self._get_access_token()
        headers = {
            "Authorization": f"bearer {token}",
            "User-Agent": self.config.user_agent,
        }
        url = f"{REDDIT_API_BASE}{endpoint}"

        for attempt in range(3):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=30)
                    ) as resp:
                        if resp.status == 429:
                            retry_after = int(resp.headers.get("Retry-After", "5"))
                            logger.warning("Rate limited, sleeping %ds", retry_after)
                            await asyncio.sleep(retry_after)
                            continue

                        if resp.status >= 500:
                            wait = 2 ** attempt
                            logger.warning("Server error %d, retrying in %ds", resp.status, wait)
                            await asyncio.sleep(wait)
                            continue

                        if resp.status >= 400:
                            logger.error("Client error %d for %s", resp.status, url)
                            return {}

                        return await resp.json()

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                wait = 2 ** attempt
                logger.warning("Request failed: %s, retrying in %ds", e, wait)
                await asyncio.sleep(wait)

        logger.error("All retries exhausted for %s", url)
        return {}

    async def search_posts(self, query: SearchQuery) -> list[RawPost]:
        """Search posts by subreddit or keyword."""
        posts: list[RawPost] = []

        for subreddit in query.subreddits:
            # Strip r/ prefix if present
            sub_name = subreddit.replace("r/", "")
            endpoint = f"/r/{sub_name}/new"
            params = {"limit": min(query.limit, 100)}
            data = await self._request(endpoint, params)
            posts.extend(self._parse_listing(data))

        if query.keywords:
            for keyword in query.keywords:
                endpoint = "/search"
                params = {"q": keyword, "limit": min(query.limit, 100), "sort": "new", "type": "link"}
                data = await self._request(endpoint, params)
                posts.extend(self._parse_listing(data))

        return posts

    def _parse_listing(self, data: dict) -> list[RawPost]:
        """Parse a Reddit listing response into RawPost objects."""
        posts: list[RawPost] = []
        children = data.get("data", {}).get("children", [])
        for child in children:
            d = child.get("data", {})
            posts.append(RawPost(
                post_id=d.get("id", ""),
                title=d.get("title", ""),
                body=d.get("selftext", ""),
                author_id="[redacted]",
                created_at=d.get("created_utc", 0),
                sub_community=f"r/{d.get('subreddit', '')}",
                upvotes=d.get("ups", 0),
                comment_count=d.get("num_comments", 0),
                url=f"https://reddit.com{d.get('permalink', '')}",
                raw_json=d,
            ))
        return posts

    async def get_comments(self, post_id: str) -> list[RawComment]:
        """Get comments for a post."""
        endpoint = f"/comments/{post_id}"
        data = await self._request(endpoint)

        comments: list[RawComment] = []
        # Reddit returns [post_data, comments_data] for /comments endpoint
        if isinstance(data, list) and len(data) > 1:
            comments = self._parse_comments(data[1], post_id)
        return comments

    def _parse_comments(self, data: dict, post_id: str) -> list[RawComment]:
        """Recursively parse Reddit comment tree."""
        comments: list[RawComment] = []
        children = data.get("data", {}).get("children", [])
        for child in children:
            if child.get("kind") != "t1":
                continue
            d = child.get("data", {})
            parent_id = d.get("parent_id", "")
            # Strip t1_ or t3_ prefix
            if parent_id.startswith("t1_") or parent_id.startswith("t3_"):
                parent_id = parent_id[3:]

            comments.append(RawComment(
                comment_id=d.get("id", ""),
                post_id=post_id,
                body=d.get("body", ""),
                author_id="[redacted]",
                parent_id=parent_id,
                created_at=d.get("created_utc", 0),
                upvotes=d.get("ups", 0),
                raw_json=d,
            ))

            # Recurse into replies
            if d.get("replies") and isinstance(d["replies"], dict):
                comments.extend(self._parse_comments(d["replies"], post_id))

        return comments