from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class PostMetrics:
    upvotes: int = 0
    comment_count: int = 0


@dataclass
class CommentMetrics:
    upvotes: int = 0


@dataclass
class CommonPost:
    platform: str
    post_id: str
    title: str
    body: str
    author_id: str
    created_at: datetime
    country: str
    sub_community: str
    metrics: PostMetrics = field(default_factory=PostMetrics)
    raw_json: dict = field(default_factory=dict)


@dataclass
class CommonComment:
    platform: str
    comment_id: str
    post_id: str
    body: str
    author_id: str
    created_at: datetime
    metrics: CommentMetrics = field(default_factory=CommentMetrics)
    parent_id: str | None = None
    raw_json: dict = field(default_factory=dict)