from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class SearchQuery:
    """Parameters for a crawl search."""
    subreddits: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    country: str = "us"
    limit: int = 100


@dataclass
class RawPost:
    """Platform-agnostic raw post data from an adapter."""
    post_id: str
    title: str
    body: str
    created_at: float  # Unix timestamp
    sub_community: str
    author_id: str = "[redacted]"
    upvotes: int = 0
    comment_count: int = 0
    url: str = ""
    raw_json: dict = field(default_factory=dict)


@dataclass
class RawComment:
    """Platform-agnostic raw comment data from an adapter."""
    comment_id: str
    post_id: str
    body: str
    created_at: float  # Unix timestamp
    author_id: str = "[redacted]"
    parent_id: str | None = None
    upvotes: int = 0
    raw_json: dict = field(default_factory=dict)


class BaseAdapter(ABC):
    """Abstract base for all platform adapters."""

    platform: str

    @abstractmethod
    async def search_posts(self, query: SearchQuery) -> list[RawPost]:
        """Search for posts matching the query."""
        ...

    @abstractmethod
    async def get_comments(self, post_id: str) -> list[RawComment]:
        """Get all comments for a post."""
        ...