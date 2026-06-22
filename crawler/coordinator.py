import asyncio
import logging
from dataclasses import dataclass, field

from crawler.base import BaseAdapter, SearchQuery, RawPost, RawComment
from pipeline.dedup import dedup_posts, dedup_comments

logger = logging.getLogger(__name__)


@dataclass
class CrawlResult:
    """Result of a crawl operation."""
    platform: str
    posts: list[RawPost] = field(default_factory=list)
    comments: list[RawComment] = field(default_factory=list)
    total_posts: int = 0
    total_comments: int = 0


class CrawlCoordinator:
    """Routes crawl requests to the appropriate platform adapter."""

    def __init__(self, adapters: dict[str, BaseAdapter]):
        self.adapters = adapters

    async def run_crawl(self, query: SearchQuery, platform: str = "reddit") -> CrawlResult:
        """Execute a full crawl for a given platform and query."""
        adapter = self.adapters.get(platform)
        if not adapter:
            raise ValueError(f"Unknown platform: {platform}")

        logger.info("Starting crawl for platform=%s, subreddits=%s, keywords=%s",
                     platform, query.subreddits, query.keywords)

        # Step 1: Search posts (each subreddit concurrently)
        subreddit_tasks = []
        for subreddit in query.subreddits:
            sub_query = SearchQuery(
                subreddits=[subreddit],
                keywords=query.keywords,
                country=query.country,
                limit=query.limit,
            )
            subreddit_tasks.append(adapter.search_posts(sub_query))

        # Also search keywords globally if no subreddits specified
        keyword_tasks = []
        if not query.subreddits and query.keywords:
            kw_query = SearchQuery(
                keywords=query.keywords,
                country=query.country,
                limit=query.limit,
            )
            keyword_tasks.append(adapter.search_posts(kw_query))

        all_tasks = subreddit_tasks + keyword_tasks
        if all_tasks:
            post_batches = await asyncio.gather(*all_tasks)
            all_posts: list[RawPost] = []
            for batch in post_batches:
                all_posts.extend(batch)
        else:
            all_posts = []

        # Step 2: Deduplicate posts
        all_posts = dedup_posts(all_posts)
        logger.info("Found %d unique posts", len(all_posts))

        # Step 3: Fetch comments for each post concurrently
        comment_tasks = [adapter.get_comments(p.post_id) for p in all_posts]
        comment_batches = await asyncio.gather(*comment_tasks)
        all_comments: list[RawComment] = []
        for batch in comment_batches:
            all_comments.extend(batch)

        # Step 4: Deduplicate comments
        all_comments = dedup_comments(all_comments)
        logger.info("Found %d unique comments", len(all_comments))

        return CrawlResult(
            platform=platform,
            posts=all_posts,
            comments=all_comments,
            total_posts=len(all_posts),
            total_comments=len(all_comments),
        )