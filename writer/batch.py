import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from writer.db import Platform, Post, Comment

logger = logging.getLogger(__name__)


class BatchWriter:
    """Handles batch insertion of crawled data into PostgreSQL."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert_platform(self, name: str) -> int:
        """Get or create a platform, return its ID."""
        result = await self.session.execute(
            select(Platform.id).where(Platform.name == name)
        )
        row = result.first()
        if row:
            return row[0]
        platform = Platform(name=name)
        self.session.add(platform)
        await self.session.flush()
        return platform.id

    async def insert_posts(self, posts: list[Post]) -> None:
        """Insert posts, skipping duplicates on (platform_id, post_id)."""
        if not posts:
            return
        for post in posts:
            self.session.add(post)
        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            # Retry one-by-one to skip duplicates
            for post in posts:
                try:
                    self.session.add(post)
                    await self.session.commit()
                except Exception:
                    await self.session.rollback()
                    logger.debug("Skipping duplicate post: %s", post.post_id)

    async def insert_comments(self, comments: list[Comment]) -> None:
        """Insert comments, skipping duplicates."""
        if not comments:
            return
        for comment in comments:
            self.session.add(comment)
        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            for comment in comments:
                try:
                    self.session.add(comment)
                    await self.session.commit()
                except Exception:
                    await self.session.rollback()
                    logger.debug("Skipping duplicate comment: %s", comment.comment_id)