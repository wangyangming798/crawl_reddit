from datetime import datetime, timezone
from crawler.base import RawPost, RawComment
from pipeline.models import CommonPost, CommonComment, PostMetrics, CommentMetrics

PLATFORM_IDS = {
    "reddit": 1,
    "twitter": 2,
    "facebook": 3,
}


def platform_id_for_name(name: str) -> int:
    """Map platform name to its database ID."""
    return PLATFORM_IDS.get(name, 1)


def _ts_to_datetime(timestamp: float) -> datetime:
    """Convert Unix timestamp to UTC datetime."""
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


def normalize_post(raw: RawPost, platform: str, country: str) -> CommonPost:
    """Convert a RawPost into a CommonPost."""
    return CommonPost(
        platform=platform,
        post_id=raw.post_id,
        title=raw.title,
        body=raw.body,
        author_id=raw.author_id,
        created_at=_ts_to_datetime(raw.created_at),
        country=country,
        sub_community=raw.sub_community,
        metrics=PostMetrics(
            upvotes=raw.upvotes,
            comment_count=raw.comment_count,
        ),
        raw_json=raw.raw_json,
    )


def normalize_comment(raw: RawComment, platform: str) -> CommonComment:
    """Convert a RawComment into a CommonComment."""
    return CommonComment(
        platform=platform,
        comment_id=raw.comment_id,
        post_id=raw.post_id,
        body=raw.body,
        author_id=raw.author_id,
        parent_id=raw.parent_id,
        created_at=_ts_to_datetime(raw.created_at),
        metrics=CommentMetrics(upvotes=raw.upvotes),
        raw_json=raw.raw_json,
    )